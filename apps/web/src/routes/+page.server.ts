import { bot } from "#lib/server/bot.ts";
import { inviteUrl } from "#lib/server/discord.ts";
import { health } from "@square/api-client";
import type { PageServerLoad } from "./$types";

const TTL = 30_000;
let cached: { at: number; servers: Promise<number | null> } | undefined;

function serverCount() {
    if (!cached || Date.now() - cached.at > TTL) {
        cached = {
            at: Date.now(),
            servers: health({ client: bot }).then(
                ({ data }) => (data?.ready ? data.guilds : null),
                () => null,
            ),
        };
    }
    return cached.servers;
}

export const load: PageServerLoad = () => ({ inviteUrl: inviteUrl().href, servers: serverCount() });
