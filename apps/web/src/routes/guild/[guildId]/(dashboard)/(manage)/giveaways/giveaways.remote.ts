import { forGuild, read } from "#lib/server/bot.ts";
import { command, query, requested } from "$app/server";
import * as sdk from "@square/api-client";
import * as schema from "@square/api-client/zod";
import { z } from "zod";

const snowflake = z.string().regex(/^\d{17,20}$/);
const MAX_ID = 2_147_483_647;
const one = z.object({ guild: snowflake, id: z.int().min(1).max(MAX_ID) });
const path = ({ guild, id }: z.infer<typeof one>) => ({ ...forGuild(guild), path: { guild_id: guild, giveaway_id: id } });

export const giveawayList = query(
    z.object({
        guild: snowflake,
        status: z.enum(["scheduled", "running", "ended", "all"]),
        q: z.string().max(100),
        page: z.int().min(1).max(100_000),
    }),
    ({ guild, q, ...params }) => read(sdk.listGiveaways({ ...forGuild(guild), query: { ...params, ...(q.trim() && { q: q.trim() }) } })),
);

export const giveaway = query(one, (args) => read(sdk.getGiveaway(path(args))));

export const entrantList = query(
    one.extend({
        q: z.string().max(100),
        sort: z.enum(["entered", "entries"]),
        order: z.enum(["asc", "desc"]),
        page: z.int().min(1).max(100_000),
    }),
    ({ guild, id, q, ...params }) => read(sdk.listEntrants({ ...path({ guild, id }), query: { ...params, ...(q.trim() && { q: q.trim() }) } })),
);

async function refreshed<T>(result: Promise<T>) {
    const done = await result;
    await Promise.all([requested(giveawayList, 4).refreshAll(), requested(giveaway, 1).refreshAll(), requested(entrantList, 1).refreshAll()]);
    return done;
}

export const createGiveaway = command(schema.zGiveawayCreate.extend({ guild: snowflake }), ({ guild, ...body }) =>
    read(sdk.createGiveaway({ ...forGuild(guild), body })),
);

export const updateGiveaway = command(one.extend({ changes: schema.zGiveawayPatch }), ({ changes, ...args }) =>
    read(sdk.updateGiveaway({ ...path(args), body: changes })),
);

export const startGiveaway = command(one, (args) => refreshed(read(sdk.startGiveaway(path(args)))));
export const endGiveaway = command(one, (args) => refreshed(read(sdk.endGiveaway(path(args)))));
export const rerollGiveaway = command(one.extend({ userIds: z.array(snowflake).max(50).nullable() }), ({ userIds, ...args }) =>
    refreshed(read(sdk.rerollGiveaway({ ...path(args), body: { userIds } }))),
);
export const deleteGiveaway = command(one, (args) => refreshed(read(sdk.deleteGiveaway(path(args)))));

export const setEntrantBonus = command(one.extend(schema.zEntrantBonus.shape), ({ userIds, bonus, ...args }) =>
    refreshed(read(sdk.setEntrantBonus({ ...path(args), body: { userIds, bonus } }))),
);
export const removeEntrants = command(one.extend(schema.zEntrantRemove.shape), ({ userIds, ...args }) =>
    refreshed(read(sdk.removeEntrants({ ...path(args), body: { userIds } }))),
);
