import { forGuild } from "#lib/server/bot.ts";
import { streamFile } from "#lib/server/files.ts";
import * as sdk from "@square/api-client";
import { error } from "@sveltejs/kit";
import type { RequestHandler } from "./$types";

const SNOWFLAKE = /^\d{17,20}$/;

export const GET: RequestHandler = async ({ params, request }) => {
    const number = Number(params.number);
    if (!SNOWFLAKE.test(params.guildId) || !SNOWFLAKE.test(params.file) || !Number.isInteger(number) || number < 1) error(404, "Not found");

    const guild = forGuild(params.guildId);
    return streamFile(request, ({ headers, signal }) =>
        sdk.ticketFile({
            ...guild,
            headers: { ...guild.headers, ...headers },
            path: { guild_id: params.guildId, number, attachment_id: params.file },
            parseAs: "stream",
            signal,
        }),
    );
};
