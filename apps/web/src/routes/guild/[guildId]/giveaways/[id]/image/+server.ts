import { forGuild } from "#lib/server/bot.ts";
import { streamFile } from "#lib/server/files.ts";
import * as sdk from "@square/api-client";
import { error } from "@sveltejs/kit";
import type { RequestHandler } from "./$types";

const SNOWFLAKE = /^\d{17,20}$/;
const MAX_ID = 2_147_483_647;

export const GET: RequestHandler = async ({ params, request }) => {
    const id = Number(params.id);
    if (!SNOWFLAKE.test(params.guildId) || !Number.isInteger(id) || id < 1 || id > MAX_ID) error(404, "Not found");

    const guild = forGuild(params.guildId);
    return streamFile(request, ({ headers, signal }) =>
        sdk.giveawayImage({
            ...guild,
            headers: { ...guild.headers, ...headers },
            path: { guild_id: params.guildId, giveaway_id: id },
            parseAs: "stream",
            signal,
        }),
    );
};
