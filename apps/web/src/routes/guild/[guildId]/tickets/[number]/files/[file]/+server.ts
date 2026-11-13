import { forGuild, read } from "#lib/server/bot.ts";
import * as sdk from "@square/api-client";
import { error } from "@sveltejs/kit";
import type { RequestHandler } from "./$types";

const SNOWFLAKE = /^\d{17,20}$/;
const PICTURES = new Set(["image/png", "image/jpeg", "image/gif", "image/webp"]);

export const GET: RequestHandler = async ({ params }) => {
    const number = Number(params.number);
    if (!SNOWFLAKE.test(params.guildId) || !SNOWFLAKE.test(params.file) || !Number.isInteger(number) || number < 1) error(404, "Not found");

    const file = (await read(
        sdk.ticketFile({ ...forGuild(params.guildId), path: { guild_id: params.guildId, number, attachment_id: params.file }, parseAs: "blob" }),
    )) as Blob;
    return new Response(file, {
        headers: {
            // Someone in a ticket uploaded this, so it's only ever served as a picture and never as a page
            "content-type": PICTURES.has(file.type) ? file.type : "application/octet-stream",
            "x-content-type-options": "nosniff",
            "content-security-policy": "default-src 'none'; sandbox",
            "cache-control": "private, max-age=86400, immutable",
        },
    });
};
