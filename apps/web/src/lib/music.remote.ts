import { actor, bot, read, refused } from "#lib/server/bot.ts";
import { watch, watchStatus } from "#lib/server/live.ts";
import { command, query } from "$app/server";
import * as sdk from "@square/api-client";
import * as schema from "@square/api-client/zod";
import { z } from "zod";

const guildId = z.string().regex(/^\d{17,20}$/);
const forGuild = z.object({ guild: guildId });

export const livePlayer = query.live(guildId, (guild) => watch(guild, actor(), "player"));

export const liveQueue = query.live(guildId, (guild) => watch(guild, actor(), "queue"));

export const liveHistory = query.live(guildId, (guild) => watch(guild, actor(), "history"));

export const liveStatus = query.live(() => {
    actor();
    return watchStatus();
});

type Base = { client: typeof bot; path: { guild_id: string }; headers: { "x-actor-id": string } };
type Result = { data?: sdk.Done; error?: unknown; response?: Response; request?: Request };

function control<Input extends z.ZodObject<{ guild: typeof guildId }>>(
    input: Input,
    send: (body: Omit<z.infer<Input>, "guild">, base: Base) => Promise<Result>,
) {
    return command(input, async (args) => {
        const { guild, ...body } = args as z.output<Input>;
        const result = await send(body, { client: bot, path: { guild_id: guild }, headers: { "x-actor-id": actor() } });
        if (result.data) return { message: result.data.message, note: result.data.note ?? null };
        refused(result);
    });
}

export const eqPresets = query(guildId, (guild) =>
    read(sdk.eqPresets({ client: bot, path: { guild_id: guild }, headers: { "x-actor-id": actor() } })),
);

export const searchMusic = query(
    forGuild.extend({ query: z.string().min(1).max(500), source: schema.zSearchMusicQuery.shape.source }),
    ({ guild, query, source }) =>
        read(sdk.searchMusic({ client: bot, path: { guild_id: guild }, headers: { "x-actor-id": actor() }, query: { q: query, source } })),
);

export const playQuery = control(schema.zPlayQuery.extend(forGuild.shape), (body, base) => sdk.playQuery({ ...base, body }));
export const replayTrack = control(schema.zQueuedTrack.extend(forGuild.shape), (body, base) => sdk.replayTrack({ ...base, body }));

export const setPaused = control(schema.zPaused.extend(forGuild.shape), (body, base) => sdk.pausePlayer({ ...base, body }));
export const stopPlayer = control(forGuild, (_, base) => sdk.stopPlayer(base));
export const skipTrack = control(forGuild, (_, base) => sdk.skipTrack(base));
export const previousTrack = control(forGuild, (_, base) => sdk.previousTrack(base));
export const seekTrack = control(schema.zSeek.extend(forGuild.shape), (body, base) => sdk.seekTrack({ ...base, body }));
export const setVolume = control(schema.zVolume.extend(forGuild.shape), (body, base) => sdk.setVolume({ ...base, body }));
export const setLoop = control(schema.zLoopMode.extend(forGuild.shape), (body, base) => sdk.setLoop({ ...base, body }));
export const setShuffle = control(schema.zToggle.extend(forGuild.shape), (body, base) => sdk.setShuffle({ ...base, body }));
export const setAutoplay = control(schema.zToggle.extend(forGuild.shape), (body, base) => sdk.setAutoplay({ ...base, body }));
export const setEq = control(schema.zEqToggle.extend(forGuild.shape), (body, base) => sdk.setEq({ ...base, body }));
export const resetEq = control(forGuild, (_, base) => sdk.resetEq(base));

export const jumpToTrack = control(schema.zQueuedTrack.extend(forGuild.shape), (body, base) => sdk.jumpToTrack({ ...base, body }));
export const removeTrack = control(schema.zQueuedTrack.extend(forGuild.shape), (body, base) => sdk.removeTrack({ ...base, body }));
export const moveTrack = control(schema.zQueueMove.extend(forGuild.shape), (body, base) => sdk.moveTrack({ ...base, body }));
export const clearQueue = control(forGuild, (_, base) => sdk.clearQueue(base));
export const reverseQueue = control(forGuild, (_, base) => sdk.reverseQueue(base));
export const sortQueue = control(forGuild, (_, base) => sdk.sortQueue(base));
export const dedupeQueue = control(forGuild, (_, base) => sdk.dedupeQueue(base));
export const removeRequesterTracks = control(schema.zRequester.extend(forGuild.shape), (body, base) => sdk.removeRequesterTracks({ ...base, body }));
