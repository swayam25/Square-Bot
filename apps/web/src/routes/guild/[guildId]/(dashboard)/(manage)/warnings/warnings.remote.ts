import { forGuild, read } from "#lib/server/bot.ts";
import { command, query, requested } from "$app/server";
import * as sdk from "@square/api-client";
import * as schema from "@square/api-client/zod";
import { z } from "zod";

const snowflake = z.string().regex(/^\d{17,20}$/);
const page = z.int().min(1).max(10_000);

export const warningRanking = query(z.object({ guild: snowflake, page }), ({ guild, page }) =>
    read(sdk.warningRanking({ ...forGuild(guild), query: { page } })),
);

export const warningProfile = query(z.object({ guild: snowflake, user: snowflake, page }), ({ guild, user, page }) =>
    read(sdk.warningProfile({ ...forGuild(guild), path: { guild_id: guild, user_id: user }, query: { page } })),
);

export const giveWarning = command(schema.zWarnCreate.extend({ guild: snowflake }), async ({ guild, ...body }) => {
    const warned = await read(sdk.giveWarning({ ...forGuild(guild), body }));
    await Promise.all([requested(warningRanking, 1).refreshAll(), requested(warningProfile, 1).refreshAll()]);
    return warned;
});

// Both run from a confirm dialog, so the page refreshes once it closes (see ResetButton)
export const removeWarning = command(z.object({ guild: snowflake, user: snowflake, warning: z.int().min(1) }), ({ guild, user, warning }) =>
    read(sdk.removeWarning({ ...forGuild(guild), path: { guild_id: guild, user_id: user, warning_id: warning } })),
);

export const clearWarnings = command(z.object({ guild: snowflake, user: snowflake }), ({ guild, user }) =>
    read(sdk.clearWarnings({ ...forGuild(guild), path: { guild_id: guild, user_id: user } })),
);
