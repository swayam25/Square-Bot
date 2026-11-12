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

export function channelOptions(channels: Channel[], kinds: Channel["type"][]): Option[] {
    const categories = new Map(channels.filter((channel) => channel.type === "category").map((channel) => [channel.id, channel]));
    return channels
        .filter((channel) => kinds.includes(channel.type))
        .map((channel) => ({ channel, category: channel.parentId ? categories.get(channel.parentId) : undefined }))
        .sort((a, b) => (a.category?.position ?? -1) - (b.category?.position ?? -1) || a.channel.position - b.channel.position)
        .map(({ channel, category }) => ({ value: channel.id, label: channel.name, icon: icons[channel.type], hint: category?.name }));
}

export const textChannelOptions = (channels: Channel[]) => channelOptions(channels, ["text", "news"]);

export function roleOptions(roles: Role[], { assignable = false, keep = [] }: { assignable?: boolean; keep?: string[] } = {}): Option[] {
    return roles
        .filter((role) => keep.includes(role.id) || (assignable ? role.assignable : !role.managed))
        .map((role) => ({ value: role.id, label: role.name, color: role.color ?? "var(--color-mist-400)" }));
}
