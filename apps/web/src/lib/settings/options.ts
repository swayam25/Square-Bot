import type { Option } from "#lib/components/ui/Select.svelte";
import { plural } from "#lib/format.ts";
import type { Permission, SquarePermissions } from "#lib/permissions.ts";
import type { Channel, Role } from "@square/api-client";
import MaterialSymbolsBlockRounded from "~icons/material-symbols/block-rounded";
import MaterialSymbolsCampaignRounded from "~icons/material-symbols/campaign-rounded";
import MaterialSymbolsFolderRounded from "~icons/material-symbols/folder-rounded";
import MaterialSymbolsGraphicEqRounded from "~icons/material-symbols/graphic-eq-rounded";
import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
import MaterialSymbolsVolumeUpRounded from "~icons/material-symbols/volume-up-rounded";

export const OFF = "off";

export const off = (label = "Off"): Option => ({ value: OFF, label, icon: MaterialSymbolsBlockRounded });
export const picked = (value: string | null) => (value === OFF ? null : value);

const icons: Partial<Record<Channel["type"], Option["icon"]>> = {
    text: MaterialSymbolsTagRounded,
    news: MaterialSymbolsCampaignRounded,
    voice: MaterialSymbolsVolumeUpRounded,
    stage_voice: MaterialSymbolsGraphicEqRounded,
    category: MaterialSymbolsFolderRounded,
};

const isVoice = (channel: Channel) => channel.type === "voice" || channel.type === "stage_voice";

/** Discord's own order: channels without a category first, then each category with its channels, text before voice. */
export function channelOptions(channels: Channel[], kinds: Channel["type"][]): Option[] {
    const categories = channels.filter((channel) => channel.type === "category").sort((a, b) => a.position - b.position);
    const known = new Set(categories.map((category) => category.id));
    const option = (channel: Channel, category?: Channel): Option => ({
        value: channel.id,
        label: channel.name,
        icon: icons[channel.type],
        hint: category?.name,
    });
    const inside = (parent: string | null) =>
        channels
            .filter((channel) => channel.type !== "category" && kinds.includes(channel.type))
            .filter((channel) => (channel.parentId && known.has(channel.parentId) ? channel.parentId : null) === parent)
            .sort((a, b) => Number(isVoice(a)) - Number(isVoice(b)) || a.position - b.position);
    return [
        ...inside(null).map((channel) => option(channel)),
        ...categories.flatMap((category) => [
            ...(kinds.includes("category") ? [option(category)] : []),
            ...inside(category.id).map((channel) => option(channel, category)),
        ]),
    ];
}

const TEXT: Channel["type"][] = ["text", "news"];

export const textChannelOptions = (channels: Channel[]) => channelOptions(channels, TEXT);

const roleOption = (role: Role): Option => ({
    value: role.id,
    label: role.name,
    ...(role.iconUrl ? { image: role.iconUrl } : role.emoji ? { emoji: role.emoji } : { color: role.color ?? "var(--color-gray-400)" }),
});

export function roleOptions(roles: Role[], { keep = [] }: { keep?: string[] } = {}): Option[] {
    return roles.filter((role) => keep.includes(role.id) || !role.managed).map(roleOption);
}

export type ChannelNeed = "send" | "attach" | "webhook" | "play";

const CHANNEL_NEEDS: Record<ChannelNeed, { permissions: Permission[]; why: string }> = {
    send: { permissions: ["ViewChannel", "SendMessages"], why: "can't send messages in" },
    attach: { permissions: ["ViewChannel", "SendMessages", "AttachFiles"], why: "can't send files in" },
    webhook: { permissions: ["ViewChannel", "SendMessages", "ManageWebhooks"], why: "needs Manage Webhooks in" },
    play: { permissions: ["ViewChannel", "Connect", "Speak"], why: "can't connect and speak in" },
};

const canUse = (perms: SquarePermissions, channel: Channel, need: ChannelNeed) => perms.hasIn(channel.id, ...CHANNEL_NEEDS[need].permissions);

export const canUseAnyTextChannel = (channels: Channel[], perms: SquarePermissions, need: ChannelNeed) =>
    channels.some((channel) => TEXT.includes(channel.type) && canUse(perms, channel, need));

export function usableChannels(
    channels: Channel[],
    perms: SquarePermissions,
    kinds: Channel["type"][],
    need: ChannelNeed,
    keep: (string | null)[] = [],
) {
    const usable = channels.filter((channel) => channel.type === "category" || keep.includes(channel.id) || canUse(perms, channel, need));
    const hidden = channels.filter((channel) => kinds.includes(channel.type) && !usable.includes(channel)).length;
    return {
        options: channelOptions(usable, kinds),
        note: hidden ? `${plural(hidden, "channel")} hidden, Square ${CHANNEL_NEEDS[need].why} ${hidden === 1 ? "it" : "them"}.` : null,
    };
}

export const usableTextChannels = (channels: Channel[], perms: SquarePermissions, need: ChannelNeed, keep: (string | null)[] = []) =>
    usableChannels(channels, perms, TEXT, need, keep);

export function givableRoles(roles: Role[], perms: SquarePermissions, keep: string[] = []) {
    const shown = roles.filter((role) => keep.includes(role.id) || perms.canGive(role));
    const hidden = roles.filter((role) => !role.managed && !shown.includes(role)).length;
    const why = perms.reason("ManageRoles") ?? `${hidden === 1 ? "it's" : "they're"} above Square's role`;
    return { options: shown.map(roleOption), note: hidden ? `${plural(hidden, "role")} hidden, ${why}.` : null };
}
