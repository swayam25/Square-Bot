import { BOT_API_SECRET, BOT_API_URL } from "$app/env/private";
import { createClient } from "@square/api-client/client";

/**
 * The bot API client. Pass it to every SDK call, e.g. `myGuilds({ client: bot, headers: { "x-actor-id": userId } })`.
 */
export const bot = createClient({ baseUrl: BOT_API_URL, auth: BOT_API_SECRET });

// A stuck bot shouldn't hang page loads
bot.interceptors.request.use((request) => new Request(request, { signal: AbortSignal.any([request.signal, AbortSignal.timeout(5_000)]) }));
