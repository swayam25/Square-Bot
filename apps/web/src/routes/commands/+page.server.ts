import { bot } from "#lib/server/bot.ts";
import { botCommands, type CommandCategory } from "@square/api-client";
import type { PageServerLoad } from "./$types";

const TTL = 5 * 60_000;

let fresh: { at: number; categories: CommandCategory[] } | undefined;
let pending: Promise<CommandCategory[] | null> | undefined;

// A failed fetch serves the last good copy and isn't cached, so the next request tries the bot again
function fetchCommands() {
    pending ??= botCommands({ client: bot, signal: AbortSignal.timeout(3_000) })
        .then(
            ({ data }) => {
                if (data) fresh = { at: Date.now(), categories: data };
            },
            () => {},
        )
        .then(() => fresh?.categories ?? null)
        .finally(() => (pending = undefined));
    return pending;
}

export const load: PageServerLoad = async () => ({
    categories: fresh && Date.now() - fresh.at < TTL ? fresh.categories : await fetchCommands(),
});
