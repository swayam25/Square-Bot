import { BOT_API_SECRET, BOT_API_URL } from "$app/env/private";
import { createClient } from "@square/api-client/client";

export const bot = createClient({ baseUrl: BOT_API_URL, auth: BOT_API_SECRET });

bot.interceptors.request.use((request) => new Request(request, { signal: AbortSignal.any([request.signal, AbortSignal.timeout(5_000)]) }));
