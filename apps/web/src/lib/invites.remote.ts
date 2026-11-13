import { forGuild, read } from "#lib/server/bot.ts";
import { command, query } from "$app/server";
import * as sdk from "@square/api-client";
import * as schema from "@square/api-client/zod";
import { z } from "zod";

const snowflake = z.string().regex(/^\d{17,20}$/);

export const inviteLeaderboard = query(
    z.object({
        guild: snowflake,
        page: z.int().min(1).max(10_000),
        sort: z.enum(["total", "regular", "left", "fake", "bonus"]),
        order: z.enum(["asc", "desc"]),
    }),
    ({ guild, ...params }) => read(sdk.inviteLeaderboard({ ...forGuild(guild), query: params })),
);

export const inviteProfile = query(z.object({ guild: snowflake, user: snowflake }), ({ guild, user }) =>
    read(sdk.inviteProfile({ ...forGuild(guild), path: { guild_id: guild, user_id: user } })),
);

export const changeBonus = command(schema.zBonusChange.extend({ guild: snowflake }), ({ guild, ...body }) =>
    read(sdk.changeBonus({ ...forGuild(guild), body })),
);
