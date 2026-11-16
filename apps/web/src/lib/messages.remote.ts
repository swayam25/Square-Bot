import { forGuild, read } from "#lib/server/bot.ts";
import { command, query } from "$app/server";
import * as sdk from "@square/api-client";
import * as schema from "@square/api-client/zod";
import { z } from "zod";

const guildId = z.string().regex(/^\d{17,20}$/);

export const messageSender = query(guildId, (guild) => read(sdk.messageSender(forGuild(guild))));

export const sendMessage = command(z.object({ guild: guildId, message: schema.zMessageSend }), ({ guild, message }) =>
    read(sdk.sendMessage({ ...forGuild(guild), body: message })),
);
