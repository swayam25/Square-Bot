import { forGuild, read } from "#lib/server/bot.ts";
import { command, query } from "$app/server";
import * as sdk from "@square/api-client";
import * as schema from "@square/api-client/zod";
import { z } from "zod";

const snowflake = z.string().regex(/^\d{17,20}$/);

export const autorole = query(snowflake, (guild) => read(sdk.getAutorole(forGuild(guild))));

export const updateAutorole = command(schema.zAutorolePatch.extend({ guild: snowflake }), async ({ guild, ...body }) => {
    autorole(guild).set(await read(sdk.updateAutorole({ ...forGuild(guild), body })));
});

// Runs from a confirm dialog, so it returns the result instead of setting the query (see ResetButton)
export const resetAutorole = command(snowflake, (guild) => read(sdk.resetAutorole(forGuild(guild))));
