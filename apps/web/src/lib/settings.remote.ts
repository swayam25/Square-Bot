import { forGuild, read } from "#lib/server/bot.ts";
import { command, query } from "$app/server";
import * as sdk from "@square/api-client";
import * as schema from "@square/api-client/zod";
import { z } from "zod";

const guildId = z.string().regex(/^\d{17,20}$/);

export const guildChannels = query(guildId, (guild) => read(sdk.guildChannels(forGuild(guild))));
export const guildRoles = query(guildId, (guild) => read(sdk.guildRoles(forGuild(guild))));

export const searchMembers = query(z.object({ guild: guildId, q: z.string().trim().min(1).max(100) }), ({ guild, q }) =>
    read(sdk.searchMembers({ ...forGuild(guild), query: { q } })),
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
export const resetInviteCounts = command(guildId, (guild) => read(sdk.resetInviteCounts(forGuild(guild))));

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
    return { notes, settings: await read(sdk.getMusicSettings(forGuild(guild))) };
});

export const resetMusic = command(guildId, async (guild) => {
    const { notes } = await read(sdk.resetMusicSettings(forGuild(guild)));
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
    return { notes, settings: await read(sdk.getTicketSettings(forGuild(guild))) };
});

export const resetTickets = command(guildId, async (guild) => {
    const { notes } = await read(sdk.resetTicketSettings(forGuild(guild)));
    return { notes, settings: await read(sdk.getTicketSettings(forGuild(guild))) };
});

export const moduleSettings = query(guildId, (guild) => read(sdk.getModuleSettings(forGuild(guild))));

export const updateModules = command(schema.zModulePatch.extend({ guild: guildId }), async ({ guild, ...body }) => {
    moduleSettings(guild).set(await read(sdk.updateModuleSettings({ ...forGuild(guild), body })));
});
