import { bot } from "#lib/server/bot.ts";
import { botEmojis, type BotEmoji } from "@square/api-client";

const TTL = 60_000;
let cached: { at: number; emojis: Promise<Record<string, BotEmoji>> } | undefined;

// The root layout awaits this on every server render: without the short timeout and stale fallback, a slow bot stalls every page
export function squareEmojis() {
    if (!cached || Date.now() - cached.at > TTL) {
        const stale = cached?.emojis ?? Promise.resolve({});
        cached = {
            at: Date.now(),
            emojis: botEmojis({ client: bot, signal: AbortSignal.timeout(1_500) }).then(
                ({ data }) => data ?? stale,
                () => stale,
            ),
        };
    }
    return cached.emojis;
}
