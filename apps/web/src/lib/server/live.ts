import { BOT_API_SECRET, BOT_API_URL } from "$app/env/private";
import type { PlayerState, QueueState } from "@square/api-client";
import { error } from "@sveltejs/kit";
import WebSocket from "ws";

/**
 * One WebSocket to the bot carries every live query on this server. It reconnects on its own and resubscribes, so a
 * bot restart doesn't end anyone's live query: they keep their last value and pick up again once the bot is back.
 * NOTE: a live query that throws is over for good in the browser, so outages are reported through `watchStatus`.
 */

export interface Topics {
    player: PlayerState;
    queue: QueueState;
}

type Update = { id: number; data?: unknown; error?: "not_found" | "forbidden" };

const subscriptions = new Map<number, { message: string; push: (update: Update) => void }>();
const statusListeners = new Set<(online: boolean) => void>();
let socket: WebSocket | null = null;
let online = false;

// Dev reloads re-run this module, so close the socket the previous copy left open instead of leaking one per reload
const shared = globalThis as { squareLiveSocket?: WebSocket };
const stale = shared.squareLiveSocket;
shared.squareLiveSocket = undefined;
stale?.terminate();
let retries = 0;
let nextId = 0;

function setOnline(value: boolean) {
    if (online === value) return;
    online = value;
    for (const listener of statusListeners) listener(value);
}

function connect() {
    const ws = new WebSocket(new URL("/live", BOT_API_URL.replace(/^http/, "ws")), {
        headers: { Authorization: `Bearer ${BOT_API_SECRET}` },
    });
    shared.squareLiveSocket = ws;
    // uvicorn pings every 20s, so a silent socket is a dead one even if TCP hasn't noticed yet
    let alive: NodeJS.Timeout | undefined;
    const heartbeat = () => {
        clearTimeout(alive);
        alive = setTimeout(() => ws.terminate(), 30_000);
    };
    ws.on("open", () => {
        retries = 0;
        heartbeat();
        setOnline(true);
        for (const { message } of subscriptions.values()) ws.send(message);
    });
    ws.on("ping", heartbeat);
    ws.on("message", (raw) => {
        const update: Update = JSON.parse(raw.toString());
        subscriptions.get(update.id)?.push(update);
    });
    // `close` always follows, and that's where the retry happens
    ws.on("error", (err) => console.error("Bot live socket error:", err.message));
    ws.on("close", () => {
        clearTimeout(alive);
        if (shared.squareLiveSocket !== ws) return; // Replaced by a reloaded copy of this module
        socket = null;
        setOnline(false);
        if (subscriptions.size || statusListeners.size) {
            setTimeout(ensureSocket, Math.min(1000 * 2 ** retries++, 30_000));
        }
    });
    return ws;
}

function ensureSocket() {
    socket ??= connect();
    return socket;
}

/**
 * Streams a topic's snapshots for a guild, as seen by `actor`. Only the newest unread snapshot is kept, like a live
 * query. Fails with 403/404 when the user loses access, and with 503 when the bot doesn't answer the first time.
 */
export async function* watch<T extends keyof Topics>(guild: string, actor: string, topic: T): AsyncGenerator<Topics[T]> {
    const id = ++nextId;
    const message = JSON.stringify({ op: "sub", id, guild, actor, topic });
    let latest: Update | undefined;
    let wake: (() => void) | undefined;
    subscriptions.set(id, {
        message,
        push(update) {
            latest = update;
            wake?.();
        },
    });
    const ws = ensureSocket();
    if (ws.readyState === WebSocket.OPEN) ws.send(message);

    try {
        for (let first = true; ; first = false) {
            if (!latest) {
                const arrived = new Promise<void>((resolve) => (wake = resolve));
                // The first snapshot comes straight back. Later ones can take as long as the music does
                const timeout = first ? setTimeout(() => wake?.(), 5_000) : undefined;
                await arrived;
                clearTimeout(timeout);
            }
            const update = latest;
            latest = wake = undefined;
            if (!update) error(503, "Square is offline right now");
            if (update.error === "forbidden") error(403, "You need Manage Server in this server");
            if (update.error === "not_found") error(404, "Server not found");
            yield update.data as Topics[T];
        }
    } finally {
        subscriptions.delete(id);
        if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ op: "unsub", id }));
    }
}

/**
 * Whether the bot is reachable, now and whenever that changes.
 */
export async function* watchStatus(): AsyncGenerator<boolean> {
    let changed: (() => void) | undefined;
    const listener = () => changed?.();
    statusListeners.add(listener);
    const ws = ensureSocket();
    // Let a connection that's still opening settle first, so the page doesn't flash "offline" on load
    if (ws.readyState === WebSocket.CONNECTING) {
        await Promise.race([
            new Promise((resolve) => ws.once("open", resolve).once("close", resolve)),
            new Promise((resolve) => setTimeout(resolve, 3_000)),
        ]);
    }
    try {
        while (true) {
            yield online;
            await new Promise<void>((resolve) => (changed = resolve));
        }
    } finally {
        statusListeners.delete(listener);
    }
}
