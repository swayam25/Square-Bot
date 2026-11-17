import { forGuild, read } from "#lib/server/bot.ts";
import { command, query } from "$app/server";
import * as sdk from "@square/api-client";
import * as schema from "@square/api-client/zod";
import { z } from "zod";

const snowflake = z.string().regex(/^\d{17,20}$/);
const rule = z.object({ guild: snowflake, id: snowflake });
const path = ({ guild, id }: z.infer<typeof rule>) => ({ ...forGuild(guild), path: { guild_id: guild, rule_id: id } });

export const automodSettings = query(snowflake, (guild) => read(sdk.getAutomod(forGuild(guild))));

export const discordRules = query(snowflake, (guild) => read(sdk.listNativeRules(forGuild(guild))));

export const updateAutomod = command(schema.zAutomodPatch.extend({ guild: snowflake }), ({ guild, ...body }) =>
    read(sdk.updateAutomod({ ...forGuild(guild), body })),
);

// Runs from a confirm dialog, so it returns the result instead of setting the query (see ResetButton)
export const resetAutomod = command(snowflake, (guild) => read(sdk.resetAutomod(forGuild(guild))));

// Returns Discord's whole list too, so rules made elsewhere in the meantime show up as well
export const createDiscordRule = command(schema.zNativeRuleCreate.extend({ guild: snowflake }), async ({ guild, ...body }) => {
    const created = await read(sdk.createNativeRule({ ...forGuild(guild), body }));
    return { created, list: await read(sdk.listNativeRules(forGuild(guild))) };
});

export const updateDiscordRule = command(rule.extend({ changes: schema.zNativeRulePatch }), ({ changes, ...args }) =>
    read(sdk.updateNativeRule({ ...path(args), body: changes })),
);

export const deleteDiscordRule = command(rule, async (args) => {
    await read(sdk.deleteNativeRule(path(args)));
    return read(sdk.listNativeRules(forGuild(args.guild)));
});

export const testAutomod = command(schema.zAutomodTest.extend({ guild: snowflake }), ({ guild, ...body }) =>
    read(sdk.testAutomod({ ...forGuild(guild), body })),
);
