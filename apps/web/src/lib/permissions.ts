import type { BotPermissions, Role } from "@square/api-client";
import type { GuildFeature, PermissionFlagsBits } from "discord-api-types/v10";

// Bit and Discord's display name. discord-api-types checks the keys, but importing its values would ship the whole package.
const PERMISSIONS = {
    CreateInstantInvite: [0, "Create Invite"],
    KickMembers: [1, "Kick Members"],
    BanMembers: [2, "Ban Members"],
    Administrator: [3, "Administrator"],
    ManageChannels: [4, "Manage Channels"],
    ManageGuild: [5, "Manage Server"],
    AddReactions: [6, "Add Reactions"],
    ViewAuditLog: [7, "View Audit Log"],
    PrioritySpeaker: [8, "Priority Speaker"],
    Stream: [9, "Video"],
    ViewChannel: [10, "View Channels"],
    SendMessages: [11, "Send Messages"],
    SendTTSMessages: [12, "Send Text-to-Speech Messages"],
    ManageMessages: [13, "Manage Messages"],
    EmbedLinks: [14, "Embed Links"],
    AttachFiles: [15, "Attach Files"],
    ReadMessageHistory: [16, "Read Message History"],
    MentionEveryone: [17, "Mention @everyone, @here and All Roles"],
    UseExternalEmojis: [18, "Use External Emojis"],
    ViewGuildInsights: [19, "View Server Insights"],
    Connect: [20, "Connect"],
    Speak: [21, "Speak"],
    MuteMembers: [22, "Mute Members"],
    DeafenMembers: [23, "Deafen Members"],
    MoveMembers: [24, "Move Members"],
    UseVAD: [25, "Use Voice Activity"],
    ChangeNickname: [26, "Change Nickname"],
    ManageNicknames: [27, "Manage Nicknames"],
    ManageRoles: [28, "Manage Roles"],
    ManageWebhooks: [29, "Manage Webhooks"],
    ManageGuildExpressions: [30, "Manage Expressions"],
    UseApplicationCommands: [31, "Use Application Commands"],
    RequestToSpeak: [32, "Request to Speak"],
    ManageEvents: [33, "Manage Events"],
    ManageThreads: [34, "Manage Threads"],
    CreatePublicThreads: [35, "Create Public Threads"],
    CreatePrivateThreads: [36, "Create Private Threads"],
    UseExternalStickers: [37, "Use External Stickers"],
    SendMessagesInThreads: [38, "Send Messages in Threads"],
    UseEmbeddedActivities: [39, "Use Activities"],
    ModerateMembers: [40, "Timeout Members"],
    ViewCreatorMonetizationAnalytics: [41, "View Server Subscription Insights"],
    UseSoundboard: [42, "Use Soundboard"],
    CreateGuildExpressions: [43, "Create Expressions"],
    CreateEvents: [44, "Create Events"],
    UseExternalSounds: [45, "Use External Sounds"],
    SendVoiceMessages: [46, "Send Voice Messages"],
    SetVoiceChannelStatus: [48, "Set Voice Channel Status"],
    SendPolls: [49, "Create Polls"],
    UseExternalApps: [50, "Use External Apps"],
    PinMessages: [51, "Pin Messages"],
    BypassSlowmode: [52, "Bypass Slowmode"],
} as const satisfies Partial<Record<keyof typeof PermissionFlagsBits, readonly [number, string]>>;

export type Permission = keyof typeof PERMISSIONS;
export type Feature = `${GuildFeature}`;

const flag = (name: Permission) => 1n << BigInt(PERMISSIONS[name][0]);
const ADMINISTRATOR = flag("Administrator");
const list = new Intl.ListFormat("en", { type: "conjunction" });

export const permissionName = (name: Permission) => PERMISSIONS[name][1];

function holds(bits: bigint | undefined, need: Permission[]) {
    if (bits === undefined) return false;
    if (bits & ADMINISTRATOR) return true;
    const wanted = need.reduce((all, name) => all | flag(name), 0n);
    return (bits & wanted) === wanted;
}

export class SquarePermissions {
    readonly #guild: bigint | undefined;
    readonly #channels: Map<string, bigint>;
    readonly #topRole: number;
    readonly #features: ReadonlySet<string>;

    constructor(raw: BotPermissions | undefined) {
        this.#guild = raw && BigInt(raw.guild);
        this.#channels = new Map(Object.entries(raw?.channels ?? {}).map(([id, bits]) => [id, BigInt(bits)]));
        this.#topRole = raw?.topRole ?? 0;
        this.#features = new Set(raw?.features);
    }

    has(...need: Permission[]) {
        return holds(this.#guild, need);
    }

    reason(...need: Permission[]) {
        const missing = need.filter((name) => !this.has(name));
        if (!missing.length) return null;
        return `Square needs the ${list.format(missing.map(permissionName))} permission${missing.length > 1 ? "s" : ""}`;
    }

    hasIn(channelId: string, ...need: Permission[]) {
        return holds(this.#channels.get(channelId), need);
    }

    canGive(role: Role) {
        return this.has("ManageRoles") && !role.managed && role.position < this.#topRole;
    }

    hasFeature(feature: Feature) {
        return this.#features.has(feature);
    }
}
