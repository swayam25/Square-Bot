import type { Option } from "#lib/components/ui/Select.svelte";
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

export const textChannelOptions = (channels: Channel[]) => channelOptions(channels, ["text", "news"]);

export function roleOptions(roles: Role[], { assignable = false, keep = [] }: { assignable?: boolean; keep?: string[] } = {}): Option[] {
    return roles
        .filter((role) => keep.includes(role.id) || (assignable ? role.assignable : !role.managed))
        .map((role) => ({ value: role.id, label: role.name, color: role.color ?? "var(--color-gray-400)" }));
}
