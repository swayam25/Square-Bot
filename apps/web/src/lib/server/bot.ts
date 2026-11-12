import { BOT_API_SECRET, BOT_API_URL } from "$app/env/private";
import { getRequestEvent } from "$app/server";
import { createClient } from "@square/api-client/client";
import { zProblem } from "@square/api-client/zod";
import { error } from "@sveltejs/kit";

export const bot = createClient({ baseUrl: BOT_API_URL, auth: BOT_API_SECRET });

// Reads answer from the bot's memory. Writes and searches wait on Discord or Lavalink, so they get longer
const QUICK = 5_000;
const PATIENT = 30_000;

bot.interceptors.request.use((request) => {
    const quick = request.method === "GET" && !new URL(request.url).pathname.endsWith("/music/search");
    return new Request(request, { signal: AbortSignal.any([request.signal, AbortSignal.timeout(quick ? QUICK : PATIENT)]) });
});

export function actor() {
    const { session } = getRequestEvent().locals;
    if (!session) error(401, "Log in first");
    return session.user.id;
}

export function forGuild(guild: string) {
    return { client: bot, path: { guild_id: guild }, headers: { "x-actor-id": actor() } };
}

// Only refusals (409, 422) and outages (503) carry wording meant for people; the rest is framework text
const FALLBACK: Record<number, string> = {
    400: "That didn't go through. Refresh the page and try again.",
    403: "You don't have access to that anymore.",
    404: "Square isn't in this server anymore.",
    503: "Square is offline right now.",
};

// A timeout isn't an outage. The bot is up, and a write may still go through
function gaveUp(result: { error?: unknown; request?: Request }): never {
    if (!(result.error instanceof DOMException && result.error.name === "TimeoutError")) error(503, FALLBACK[503]);
    if (result.request?.method === "GET") error(504, "Square is taking too long to answer. Try again in a moment.");
    error(504, "Square is taking longer than usual. This may still go through, so check before trying again.");
}

export function refused(result: { error?: unknown; response?: Response; request?: Request }): never {
    if (!result.response) gaveUp(result);
    const { status } = result.response;
    const problem = zProblem.safeParse(result.error);
    const ours = problem.success && (status === 409 || status === 422 || status === 503);
    error(status, ours ? problem.data.detail : (FALLBACK[status] ?? "Square couldn't do that. Try again."));
}

export async function read<T>(
    request: Promise<{ data: T; error: undefined } | { data: undefined; error: unknown; response?: Response; request?: Request }>,
) {
    const result = await request;
    if (result.data === undefined) refused(result);
    return result.data;
}
