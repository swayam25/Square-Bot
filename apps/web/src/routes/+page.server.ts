import { bot } from "#lib/server/bot.ts";
import { inviteUrl } from "#lib/server/discord.ts";
import { health } from "@square/api-client";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = () => ({
    inviteUrl: inviteUrl().href,
    // Streamed, so a slow or offline bot never holds the page back. It just shows no count
    servers: health({ client: bot }).then(
        ({ data }) => (data?.ready ? data.guilds : null),
        () => null,
    ),
});
