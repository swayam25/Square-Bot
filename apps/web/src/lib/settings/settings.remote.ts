import { inviteLeaderboard } from "#lib/invites/invites.remote.ts";
import { forGuild, read } from "#lib/server/bot.ts";
import { command, query, requested } from "$app/server";
import * as sdk from "@square/api-client";
import * as schema from "@square/api-client/zod";
import { z } from "zod";

const guildId = z.string().regex(/^\d{17,20}$/);

export const guildChannels = query(guildId, (guild) => read(sdk.guildChannels(forGuild(guild))));
export const guildRoles = query(guildId, (guild) => read(sdk.guildRoles(forGuild(guild))));

export const searchMembers = query(z.object({ guild: guildId, q: z.string().trim().min(1).max(100) }), ({ guild, q }) =>
    read(sdk.searchMembers({ ...forGuild(guild), query: { q } })),
);

const BATCH = 100;
const mention = z.object({ guild: guildId, id: guildId });

// Mentions drawn together reach the bot as one request per server
function byGuild<T extends { id: string }>(load: (guild: string, ids: string[]) => Promise<T[]>) {
    return async (wanted: z.infer<typeof mention>[]) => {
        const found = new Map<string, T>();
        await Promise.all(
            [...Map.groupBy(wanted, (entry) => entry.guild)].flatMap(([guild, entries]) => {
                const ids = [...new Set(entries.map((entry) => entry.id))];
                return Array.from({ length: Math.ceil(ids.length / BATCH) }, async (_, index) => {
                    for (const item of await load(guild, ids.slice(index * BATCH, (index + 1) * BATCH))) found.set(`${guild}:${item.id}`, item);
                });
            }),
        );
        return ({ guild, id }: z.infer<typeof mention>) => found.get(`${guild}:${id}`) ?? null;
    };
}

export const mentionedUser = query.batch(
    mention,
    byGuild((guild, ids) => read(sdk.mentionedUsers({ ...forGuild(guild), query: { ids } }))),
);
export const mentionedChannel = query.batch(
    mention,
    byGuild((guild, ids) => read(sdk.mentionedChannels({ ...forGuild(guild), query: { ids } }))),
);

export const generalSettings = query(guildId, (guild) => read(sdk.getGeneralSettings(forGuild(guild))));

export const updateGeneral = command(schema.zGeneralPatch.extend({ guild: guildId }), async ({ guild, ...body }) => {
    generalSettings(guild).set(await read(sdk.updateGeneralSettings({ ...forGuild(guild), body })));
});

export const resetGeneral = command(guildId, (guild) => read(sdk.resetGeneralSettings(forGuild(guild))));

export const logSettings = query(guildId, (guild) => read(sdk.getLogSettings(forGuild(guild))));

export const updateLogs = command(schema.zLogPatch.extend({ guild: guildId }), async ({ guild, ...body }) => {
    logSettings(guild).set(await read(sdk.updateLogSettings({ ...forGuild(guild), body })));
});

export const resetLogs = command(guildId, (guild) => read(sdk.resetLogSettings(forGuild(guild))));

export const inviteSettings = query(guildId, (guild) => read(sdk.getInviteSettings(forGuild(guild))));

export const updateInvites = command(schema.zInvitePatch.extend({ guild: guildId }), async ({ guild, ...body }) => {
    inviteSettings(guild).set(await read(sdk.updateInviteSettings({ ...forGuild(guild), body })));
});

export const resetInvites = command(guildId, (guild) => read(sdk.resetInviteSettings(forGuild(guild))));
export const resetInviteCounts = command(guildId, async (guild) => {
    const reset = await read(sdk.resetInviteCounts(forGuild(guild)));
    await requested(inviteLeaderboard, 1).refreshAll();
    return reset;
});

export const musicSettings = query(guildId, (guild) => read(sdk.getMusicSettings(forGuild(guild))));

export const updateMusic = command(schema.zMusicPatch.extend({ guild: guildId }), async ({ guild, ...body }) => {
    musicSettings(guild).set(await read(sdk.updateMusicSettings({ ...forGuild(guild), body })));
});

export const createRequestChannel = command(guildId, async (guild) => {
    musicSettings(guild).set(await read(sdk.createRequestChannel(forGuild(guild))));
    await guildChannels(guild).refresh();
});

// These run from a confirm dialog, so they return the fresh settings instead of setting the query (see ResetButton)
export const removeRequestChannel = command(guildId, async (guild) => {
    const { notes } = await read(sdk.removeRequestChannel(forGuild(guild)));
    await guildChannels(guild).refresh();
    return { notes, settings: await read(sdk.getMusicSettings(forGuild(guild))) };
});

export const resetMusic = command(guildId, async (guild) => {
    const { notes } = await read(sdk.resetMusicSettings(forGuild(guild)));
    await guildChannels(guild).refresh();
    return { notes, settings: await read(sdk.getMusicSettings(forGuild(guild))) };
});

export const ticketSettings = query(guildId, (guild) => read(sdk.getTicketSettings(forGuild(guild))));

export const updateTickets = command(schema.zTicketPatch.extend({ guild: guildId }), async ({ guild, ...body }) => {
    ticketSettings(guild).set(await read(sdk.updateTicketSettings({ ...forGuild(guild), body })));
});

export const createTicketPanel = command(guildId, async (guild) => {
    ticketSettings(guild).set(await read(sdk.createTicketPanel(forGuild(guild))));
    await guildChannels(guild).refresh();
});

export const removeTicketPanel = command(guildId, async (guild) => {
    const { notes } = await read(sdk.removeTicketPanel(forGuild(guild)));
    await guildChannels(guild).refresh();
    return { notes, settings: await read(sdk.getTicketSettings(forGuild(guild))) };
});

export const resetTickets = command(guildId, async (guild) => {
    const { notes } = await read(sdk.resetTicketSettings(forGuild(guild)));
    await guildChannels(guild).refresh();
    return { notes, settings: await read(sdk.getTicketSettings(forGuild(guild))) };
});

export const resetEverything = command(guildId, async (guild) => (await read(sdk.resetAllSettings(forGuild(guild)))).notes);

export const moduleSettings = query(guildId, (guild) => read(sdk.getModuleSettings(forGuild(guild))));

export const updateModules = command(schema.zModulePatch.extend({ guild: guildId }), async ({ guild, ...body }) => {
    moduleSettings(guild).set(await read(sdk.updateModuleSettings({ ...forGuild(guild), body })));
});
