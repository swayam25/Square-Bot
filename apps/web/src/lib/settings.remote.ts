import { forGuild, read } from "#lib/server/bot.ts";
import { command, query } from "$app/server";
import * as sdk from "@square/api-client";
import * as schema from "@square/api-client/zod";
import { z } from "zod";

const guildId = z.string().regex(/^\d{17,20}$/);

export const guildChannels = query(guildId, (guild) => read(sdk.guildChannels(forGuild(guild))));
export const guildRoles = query(guildId, (guild) => read(sdk.guildRoles(forGuild(guild))));

export const generalSettings = query(guildId, (guild) => read(sdk.getGeneralSettings(forGuild(guild))));

export const updateGeneral = command(schema.zGeneralPatch.extend({ guild: guildId }), async ({ guild, ...body }) => {
    generalSettings(guild).set(await read(sdk.updateGeneralSettings({ ...forGuild(guild), body })));
});

export const resetGeneral = command(guildId, (guild) => read(sdk.resetGeneralSettings(forGuild(guild))));
