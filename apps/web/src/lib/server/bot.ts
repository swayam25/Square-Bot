import { BOT_API_SECRET, BOT_API_URL } from "$app/env/private";
import { getRequestEvent } from "$app/server";
import { createClient } from "@square/api-client/client";
import { zProblem } from "@square/api-client/zod";
import { error } from "@sveltejs/kit";

export const bot = createClient({ baseUrl: BOT_API_URL, auth: BOT_API_SECRET });

bot.interceptors.request.use((request) => new Request(request, { signal: AbortSignal.any([request.signal, AbortSignal.timeout(5_000)]) }));

export function actor() {
    const { session } = getRequestEvent().locals;
    if (!session) error(401, "Log in first");
    return session.user.id;
}

export function forGuild(guild: string) {
    return { client: bot, path: { guild_id: guild }, headers: { "x-actor-id": actor() } };
}

export function refused(result: { error?: unknown; response?: Response }): never {
    if (!result.response) error(503, "Square is offline right now");
    const problem = zProblem.safeParse(result.error);
    error(result.response.status, problem.success ? problem.data.detail : "Square couldn't do that");
}

export async function read<T>(request: Promise<{ data: T; error: undefined } | { data: undefined; error: unknown; response?: Response }>) {
    const result = await request;
    if (result.data === undefined) refused(result);
    return result.data;
}
