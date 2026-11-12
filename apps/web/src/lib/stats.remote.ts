import { forGuild, read } from "#lib/server/bot.ts";
import { query } from "$app/server";
import * as sdk from "@square/api-client";
import { z } from "zod";

const guildId = z.string().regex(/^\d{17,20}$/);

export const memberJoins = query(guildId, (guild) => read(sdk.memberJoins(forGuild(guild))));
export const serverStats = query(guildId, (guild) => read(sdk.serverStats(forGuild(guild))));
