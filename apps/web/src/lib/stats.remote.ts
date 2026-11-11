import { forGuild, read } from "#lib/server/bot.ts";
import { query } from "$app/server";
import * as sdk from "@square/api-client";
import { z } from "zod";

export const memberJoins = query(z.string().regex(/^\d{17,20}$/), (guild) => read(sdk.memberJoins(forGuild(guild))));
