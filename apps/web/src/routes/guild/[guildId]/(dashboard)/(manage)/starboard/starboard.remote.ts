import { forGuild, read } from "#lib/server/bot.ts";
import { command, query } from "$app/server";
import * as sdk from "@square/api-client";
import * as schema from "@square/api-client/zod";
import { z } from "zod";

const snowflake = z.string().regex(/^\d{17,20}$/);
const one = z.object({ guild: snowflake, id: z.int().min(1).max(2_147_483_647) });
const path = ({ guild, id }: z.infer<typeof one>) => ({ ...forGuild(guild), path: { guild_id: guild, board_id: id } });

export const starboards = query(snowflake, (guild) => read(sdk.listStarboards(forGuild(guild))));

export const createStarboard = command(schema.zStarboardCreate.extend({ guild: snowflake }), ({ guild, ...body }) =>
    read(sdk.createStarboard({ ...forGuild(guild), body })),
);

// Several boards can save at once, and the page sets the list once they're all done
export const updateStarboard = command(one.extend({ changes: schema.zStarboardPatch }), ({ changes, ...args }) =>
    read(sdk.updateStarboard({ ...path(args), body: changes })),
);

// Runs from a confirm dialog, so it returns the fresh list instead of setting the query (see ResetButton)
export const deleteStarboard = command(one, async (args) => {
    await read(sdk.deleteStarboard(path(args)));
    return read(sdk.listStarboards(forGuild(args.guild)));
});
