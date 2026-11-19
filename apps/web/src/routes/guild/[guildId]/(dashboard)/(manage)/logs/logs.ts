import type { LogChannels, LogSettings } from "@square/api-client";
import type { Component } from "svelte";
import MaterialSymbolsAccountCircleRounded from "~icons/material-symbols/account-circle-rounded";
import MaterialSymbolsAddModeratorRounded from "~icons/material-symbols/add-moderator-rounded";
import MaterialSymbolsBadgeRounded from "~icons/material-symbols/badge-rounded";
import MaterialSymbolsBlockRounded from "~icons/material-symbols/block-rounded";
import MaterialSymbolsChatRounded from "~icons/material-symbols/chat-rounded";
import MaterialSymbolsConfirmationNumberRounded from "~icons/material-symbols/confirmation-number-rounded";
import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
import MaterialSymbolsDeleteSweepRounded from "~icons/material-symbols/delete-sweep-rounded";
import MaterialSymbolsEditRounded from "~icons/material-symbols/edit-rounded";
import MaterialSymbolsGavelRounded from "~icons/material-symbols/gavel-rounded";
import MaterialSymbolsGroupRounded from "~icons/material-symbols/group-rounded";
import MaterialSymbolsHardwareRounded from "~icons/material-symbols/hardware-rounded";
import MaterialSymbolsHeadsetMicRounded from "~icons/material-symbols/headset-mic-rounded";
import MaterialSymbolsHomeStorageRounded from "~icons/material-symbols/home-storage-rounded";
import MaterialSymbolsKeepRounded from "~icons/material-symbols/keep-rounded";
import MaterialSymbolsLinkRounded from "~icons/material-symbols/link-rounded";
import MaterialSymbolsLogoutRounded from "~icons/material-symbols/logout-rounded";
import MaterialSymbolsManageAccountsRounded from "~icons/material-symbols/manage-accounts-rounded";
import MaterialSymbolsPersonAddRounded from "~icons/material-symbols/person-add-rounded";
import MaterialSymbolsPersonRemoveRounded from "~icons/material-symbols/person-remove-rounded";
import MaterialSymbolsRobot2Rounded from "~icons/material-symbols/robot-2-rounded";
import MaterialSymbolsRuleRounded from "~icons/material-symbols/rule-rounded";
import MaterialSymbolsSentimentSatisfiedRounded from "~icons/material-symbols/sentiment-satisfied-rounded";
import MaterialSymbolsShieldPersonRounded from "~icons/material-symbols/shield-person-rounded";
import MaterialSymbolsShieldRounded from "~icons/material-symbols/shield-rounded";
import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
import MaterialSymbolsTimerRounded from "~icons/material-symbols/timer-rounded";
import MaterialSymbolsVolumeOffRounded from "~icons/material-symbols/volume-off-rounded";
import MaterialSymbolsVolumeUpRounded from "~icons/material-symbols/volume-up-rounded";
import MaterialSymbolsWarningRounded from "~icons/material-symbols/warning-rounded";
import MaterialSymbolsWebhookRounded from "~icons/material-symbols/webhook-rounded";

export type LogKey = keyof LogChannels;
export type EventKey = LogSettings["disabledEvents"][number];

type Event = { key: EventKey; label: string; description: string; icon: Component; auditLog?: boolean };

export const LOGS: { key: LogKey; label: string; description: string; icon: Component; events: Event[] }[] = [
    {
        key: "moderation",
        label: "Moderation",
        description: "Bans, kicks, timeouts and warnings, with the moderator and reason.",
        icon: MaterialSymbolsHardwareRounded,
        events: [
            { key: "bans", label: "Bans", description: "Bans and unbans.", icon: MaterialSymbolsGavelRounded, auditLog: true },
            {
                key: "kicks",
                label: "Kicks",
                description: "Members kicked from the server.",
                icon: MaterialSymbolsPersonRemoveRounded,
                auditLog: true,
            },
            { key: "timeouts", label: "Timeouts", description: "Timeouts given and removed.", icon: MaterialSymbolsTimerRounded, auditLog: true },
            { key: "warnings", label: "Warnings", description: "Warnings given and removed.", icon: MaterialSymbolsWarningRounded },
        ],
    },
    {
        key: "automod",
        label: "AutoMod",
        description: "Messages caught by Discord's and Square's AutoMod rules.",
        icon: MaterialSymbolsAddModeratorRounded,
        events: [
            {
                key: "discord_rules",
                label: "Discord rules",
                description: "Discord's own AutoMod catching something.",
                icon: MaterialSymbolsShieldRounded,
            },
            { key: "square_rules", label: "Square rules", description: "Square's own rules catching something.", icon: MaterialSymbolsRuleRounded },
        ],
    },
    {
        key: "members",
        label: "Members",
        description: "People joining, leaving and changing.",
        icon: MaterialSymbolsGroupRounded,
        events: [
            { key: "joins", label: "Joins", description: "With who invited them and how old the account is.", icon: MaterialSymbolsPersonAddRounded },
            { key: "leaves", label: "Leaves", description: "With the roles they had.", icon: MaterialSymbolsLogoutRounded },
            {
                key: "nicknames",
                label: "Nicknames",
                description: "Nicknames changed, and who changed them.",
                icon: MaterialSymbolsBadgeRounded,
                auditLog: true,
            },
            {
                key: "member_roles",
                label: "Roles",
                description: "Roles added and removed, and who did it.",
                icon: MaterialSymbolsManageAccountsRounded,
                auditLog: true,
            },
            { key: "profiles", label: "Profiles", description: "Usernames, display names and avatars.", icon: MaterialSymbolsAccountCircleRounded },
        ],
    },
    {
        key: "messages",
        label: "Messages",
        description: "Edited and deleted messages. Square remembers the last 200 messages of each channel to show them.",
        icon: MaterialSymbolsChatRounded,
        events: [
            { key: "edits", label: "Edits", description: "What the message said before and after.", icon: MaterialSymbolsEditRounded },
            { key: "deletes", label: "Deletes", description: "What it said, and who deleted it.", icon: MaterialSymbolsDeleteRounded },
            {
                key: "purges",
                label: "Purges",
                description: "Many messages deleted at once, with a file of what they said.",
                icon: MaterialSymbolsDeleteSweepRounded,
            },
            { key: "pins", label: "Pins", description: "Messages pinned and unpinned.", icon: MaterialSymbolsKeepRounded, auditLog: true },
        ],
    },
    {
        key: "voice",
        label: "Voice",
        description: "Who's in which voice channel.",
        icon: MaterialSymbolsVolumeUpRounded,
        events: [
            {
                key: "voice_activity",
                label: "Activity",
                description: "Joining, leaving and switching channels.",
                icon: MaterialSymbolsHeadsetMicRounded,
            },
            {
                key: "voice_moderation",
                label: "Moderation",
                description: "Members moved, disconnected, muted or deafened by someone else.",
                icon: MaterialSymbolsVolumeOffRounded,
                auditLog: true,
            },
        ],
    },
    {
        key: "server",
        label: "Server",
        description: "Changes to the server and how it's set up.",
        icon: MaterialSymbolsHomeStorageRounded,
        events: [
            {
                key: "channels",
                label: "Channels",
                description: "Channels and threads created, changed or deleted, and their permissions.",
                icon: MaterialSymbolsTagRounded,
                auditLog: true,
            },
            {
                key: "roles",
                label: "Roles",
                description: "Roles created, changed or deleted.",
                icon: MaterialSymbolsShieldPersonRounded,
                auditLog: true,
            },
            {
                key: "server_profile",
                label: "Server profile",
                description: "Name, icon, owner and settings.",
                icon: MaterialSymbolsHomeStorageRounded,
                auditLog: true,
            },
            {
                key: "emojis",
                label: "Emojis and stickers",
                description: "Added, changed or deleted.",
                icon: MaterialSymbolsSentimentSatisfiedRounded,
                auditLog: true,
            },
            { key: "invites", label: "Invites", description: "Invite links created or deleted.", icon: MaterialSymbolsLinkRounded, auditLog: true },
            {
                key: "webhooks",
                label: "Webhooks",
                description: "Webhooks created, changed or deleted.",
                icon: MaterialSymbolsWebhookRounded,
                auditLog: true,
            },
            { key: "bots", label: "Bots", description: "Bots added to the server.", icon: MaterialSymbolsRobot2Rounded, auditLog: true },
            {
                key: "automod_rules",
                label: "AutoMod rules",
                description: "Discord AutoMod rules created, changed or deleted.",
                icon: MaterialSymbolsBlockRounded,
                auditLog: true,
            },
        ],
    },
    {
        key: "tickets",
        label: "Tickets",
        description: "Tickets opened, claimed and closed, with transcripts.",
        icon: MaterialSymbolsConfirmationNumberRounded,
        events: [],
    },
];

export const LIMITS = { channels: 50, roles: 25 };
