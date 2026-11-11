import { bot } from "#lib/server/bot.ts";
import { inviteUrl } from "#lib/server/discord.ts";
import { health } from "@square/api-client";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = () => ({
    inviteUrl: inviteUrl().href,
    servers: health({ client: bot }).then(
        ({ data }) => (data?.ready ? data.guilds : null),
        () => null,
    ),
});
