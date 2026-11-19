import { plural } from "#lib/format.ts";
import type { NativeRule, NativeRulePatch, Punishment, SquareRule } from "@square/api-client";
import type { Component } from "svelte";
import MaterialSymbolsAlternateEmailRounded from "~icons/material-symbols/alternate-email-rounded";
import MaterialSymbolsAttachFileRounded from "~icons/material-symbols/attach-file-rounded";
import MaterialSymbolsBadgeRounded from "~icons/material-symbols/badge-rounded";
import MaterialSymbolsBoltRounded from "~icons/material-symbols/bolt-rounded";
import MaterialSymbolsBrandFamilyRounded from "~icons/material-symbols/brand-family-rounded";
import MaterialSymbolsContentCopyRounded from "~icons/material-symbols/content-copy-rounded";
import MaterialSymbolsGlyphsRounded from "~icons/material-symbols/glyphs-rounded";
import MaterialSymbolsLinkOffRounded from "~icons/material-symbols/link-off-rounded";
import MaterialSymbolsMatchWordRounded from "~icons/material-symbols/match-word-rounded";
import MaterialSymbolsNotesRounded from "~icons/material-symbols/notes-rounded";
import MaterialSymbolsNotificationMultipleRounded from "~icons/material-symbols/notification-multiple-rounded";
import MaterialSymbolsNotificationsOffRounded from "~icons/material-symbols/notifications-off-rounded";
import MaterialSymbolsPermMediaRounded from "~icons/material-symbols/perm-media-rounded";
import MaterialSymbolsPersonAlertRounded from "~icons/material-symbols/person-alert-rounded";
import MaterialSymbolsPhishingRounded from "~icons/material-symbols/phishing-rounded";
import MaterialSymbolsPolicyRounded from "~icons/material-symbols/policy-rounded";
import MaterialSymbolsRepeatRounded from "~icons/material-symbols/repeat-rounded";
import MaterialSymbolsSentimentSatisfiedRounded from "~icons/material-symbols/sentiment-satisfied-rounded";
import MaterialSymbolsTextFieldsRounded from "~icons/material-symbols/text-fields-rounded";
import MaterialSymbolsVisibilityOffRounded from "~icons/material-symbols/visibility-off-rounded";

export type Kind = SquareRule["kind"];
export type Trigger = NativeRule["trigger"];
export type Mode = "simple" | "advanced";

type Bounds = { label: string; description: string; min: number; max: number };

export const KINDS: Record<Kind, { label: string; description: string; icon: Component; amount?: Bounds; seconds?: Bounds }> = {
    media: {
        label: "Media-only channels",
        description: "Messages without a file or link are removed.",
        icon: MaterialSymbolsPermMediaRounded,
    },
    invites: {
        label: "Invite links",
        description: "Invites to other servers. Invites to this server are fine.",
        icon: MaterialSymbolsLinkOffRounded,
    },
    masked_links: {
        label: "Masked links",
        description: "Links whose text shows one site but open another, a common phishing trick.",
        icon: MaterialSymbolsPhishingRounded,
    },
    new_members: {
        label: "Links from new members",
        description: "Links and files from people who joined a short while ago. Scam accounts do this.",
        icon: MaterialSymbolsPersonAlertRounded,
        amount: { label: "New for minutes", description: "Anyone who joined less than this long ago is caught.", min: 1, max: 1440 },
    },
    flood: {
        label: "Message flood",
        description: "Someone sending too many messages too fast.",
        icon: MaterialSymbolsBoltRounded,
        amount: { label: "Messages allowed", description: "The next one over this is caught.", min: 2, max: 50 },
        seconds: { label: "Within seconds", description: "How far back Square counts.", min: 2, max: 60 },
    },
    duplicates: {
        label: "Repeated messages",
        description: "The same message sent again and again, in one channel or across several.",
        icon: MaterialSymbolsContentCopyRounded,
        amount: { label: "Repeats allowed", description: "Sending it more often than this is caught.", min: 1, max: 20 },
        seconds: { label: "Within seconds", description: "How far back Square counts.", min: 5, max: 600 },
    },
    mention_flood: {
        label: "Mention flood",
        description: "Lots of pings spread over several messages. Discord's Mention spam only counts one message.",
        icon: MaterialSymbolsNotificationMultipleRounded,
        amount: { label: "Mentions allowed", description: "The next one over this is caught.", min: 2, max: 100 },
        seconds: { label: "Within seconds", description: "How far back Square counts.", min: 5, max: 300 },
    },
    file_flood: {
        label: "File spam",
        description: "Too many files and stickers in a short time.",
        icon: MaterialSymbolsAttachFileRounded,
        amount: { label: "Files allowed", description: "The next one over this is caught.", min: 2, max: 50 },
        seconds: { label: "Within seconds", description: "How far back Square counts.", min: 2, max: 60 },
    },
    ghost_pings: {
        label: "Ghost pings",
        description: "Someone pings people, then deletes the message soon after.",
        icon: MaterialSymbolsNotificationsOffRounded,
        seconds: { label: "Deleted within seconds", description: "Deleting it later than this is fine.", min: 5, max: 600 },
    },
    caps: {
        label: "Capital letters",
        description: "Messages that are mostly shouting. Messages with fewer than 10 letters are left alone.",
        icon: MaterialSymbolsTextFieldsRounded,
        amount: { label: "Most capitals", description: "Percent of letters. More than this is caught.", min: 50, max: 95 },
    },
    emojis: {
        label: "Emoji spam",
        description: "Too many emojis in one message, custom ones included.",
        icon: MaterialSymbolsSentimentSatisfiedRounded,
        amount: { label: "Most emojis", description: "More than this in one message is caught.", min: 1, max: 100 },
    },
    zalgo: {
        label: "Zalgo text",
        description: "Letters buried under stacked accent marks.",
        icon: MaterialSymbolsGlyphsRounded,
        amount: {
            label: "Most marks per letter",
            description: "More than this on one letter is caught. Some languages stack 2.",
            min: 2,
            max: 20,
        },
    },
    fonts: {
        label: "Fancy fonts",
        description: "Math, fullwidth, circled and small caps letters. They slip past word filters.",
        icon: MaterialSymbolsBrandFamilyRounded,
        amount: { label: "Most fancy letters", description: "Percent of letters. More than this is caught, 0 catches any.", min: 0, max: 90 },
    },
    repeated_chars: {
        label: "Repeated characters",
        description: "The same character over and over, like aaaaaaaaaa or !!!!!!!!!!. Code and emojis are left alone.",
        icon: MaterialSymbolsRepeatRounded,
        amount: { label: "Most in a row", description: "More than this in a row is caught.", min: 3, max: 50 },
    },
    lines: {
        label: "Walls of text",
        description: "Messages with too many lines.",
        icon: MaterialSymbolsNotesRounded,
        amount: { label: "Most lines", description: "More than this in one message is caught.", min: 3, max: 100 },
    },
    invisible: {
        label: "Invisible characters",
        description: "Zero-width and blank characters used to hide words or send empty messages.",
        icon: MaterialSymbolsVisibilityOffRounded,
    },
};

export const TRIGGERS: Record<Trigger, { label: string; description: string; icon: Component; limit: number }> = {
    keyword: {
        label: "Keywords",
        description: "Words, phrases and patterns you pick.",
        icon: MaterialSymbolsMatchWordRounded,
        limit: 6,
    },
    preset: {
        label: "Word lists",
        description: "Discord's own lists of slurs, swearing and sexual words.",
        icon: MaterialSymbolsPolicyRounded,
        limit: 1,
    },
    spam: {
        label: "Spam",
        description: "Discord's own spam detection.",
        icon: MaterialSymbolsBoltRounded,
        limit: 1,
    },
    mention_spam: {
        label: "Mention spam",
        description: "Too many people or roles pinged in one message.",
        icon: MaterialSymbolsAlternateEmailRounded,
        limit: 1,
    },
    member_profile: {
        label: "Member profiles",
        description: "Words in names, bios and pronouns.",
        icon: MaterialSymbolsBadgeRounded,
        limit: 1,
    },
};

export const TRIGGER_ORDER: Trigger[] = ["keyword", "preset", "spam", "mention_spam", "member_profile"];

export const PRESETS: { value: NativeRule["presets"][number]; label: string; description: string }[] = [
    { value: "slurs", label: "Slurs", description: "Hateful words aimed at groups of people." },
    { value: "profanity", label: "Swearing", description: "Swear words and cursing." },
    { value: "sexual_content", label: "Sexual content", description: "Sexual words and phrases." },
];

export const LIMITS = {
    keywords: 1000,
    keyword: 60,
    patterns: 10,
    pattern: 260,
    allow: 100,
    presetAllow: 1000,
    mentions: 50,
    message: 150,
    name: 100,
    nativeRoles: 20,
    nativeChannels: 50,
    roles: 25,
    channels: 50,
    mediaChannels: 10,
    punishments: 10,
    warnings: 100,
};

const MINUTE = 60;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

export const DURATIONS = [
    { value: String(MINUTE), label: "1 minute" },
    { value: String(5 * MINUTE), label: "5 minutes" },
    { value: String(10 * MINUTE), label: "10 minutes" },
    { value: String(HOUR), label: "1 hour" },
    { value: String(6 * HOUR), label: "6 hours" },
    { value: String(DAY), label: "1 day" },
    { value: String(7 * DAY), label: "1 week" },
    { value: String(28 * DAY), label: "28 days" },
];

export const durationLabel = (seconds: number) =>
    DURATIONS.find((entry) => Number(entry.value) === seconds)?.label ?? plural(Math.round(seconds / MINUTE), "minute");

export const sameJson = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);
export const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

const whole = (value: number | null, min: number, max: number) => value !== null && Number.isInteger(value) && value >= min && value <= max;

export type SquareProblems = Partial<Record<"amount" | "seconds" | "channels" | "actions", string>>;

export function squareProblems(rule: SquareRule): SquareProblems {
    const found: SquareProblems = {};
    if (!rule.enabled) return found;
    const kind = KINDS[rule.kind];
    if (kind.amount && !whole(rule.amount, kind.amount.min, kind.amount.max)) found.amount = `Pick ${kind.amount.min} to ${kind.amount.max}`;
    if (kind.seconds && !whole(rule.seconds, kind.seconds.min, kind.seconds.max)) found.seconds = `Pick ${kind.seconds.min} to ${kind.seconds.max}`;
    if (rule.kind === "media" && !rule.channelIds.length) found.channels = "Pick at least one channel";
    if (rule.kind === "ghost_pings") {
        if (!rule.notify && !rule.warn) found.actions = "Post who was pinged, warn, or both";
    } else if (!rule.delete && !rule.warn) found.actions = "Delete the message, warn, or both";
    return found;
}

export function punishmentProblems(steps: Punishment[]): Record<number, string> {
    const found: Record<number, string> = {};
    const seen = new Set<number>();
    steps.forEach((step, index) => {
        if (!whole(step.warnings, 1, LIMITS.warnings)) found[index] = `Pick 1 to ${LIMITS.warnings}`;
        else if (seen.has(step.warnings)) found[index] = "Another step uses this count";
        seen.add(step.warnings);
    });
    return found;
}

export type NativeProblems = Partial<
    Record<"name" | "keywords" | "patterns" | "allowList" | "presets" | "mentionLimit" | "blockMessage" | "actions", string>
>;

export function nativeProblems(rule: NativeRule): NativeProblems {
    const found: NativeProblems = {};
    const words = rule.trigger === "keyword" || rule.trigger === "member_profile";
    if (!rule.name.trim()) found.name = "Give the rule a name";
    else if (rule.name.length > LIMITS.name) found.name = `Up to ${LIMITS.name} characters`;
    if (words) {
        if (rule.keywords.length > LIMITS.keywords) found.keywords = `Up to ${LIMITS.keywords} words`;
        else if (rule.keywords.some((word) => word.length > LIMITS.keyword)) found.keywords = `Each word can be up to ${LIMITS.keyword} characters`;
        else if (rule.enabled && !rule.keywords.length && !rule.patterns.length) found.keywords = "Add at least one word";
        if (rule.patterns.length > LIMITS.patterns) found.patterns = `Up to ${LIMITS.patterns} patterns`;
        else if (rule.patterns.some((pattern) => pattern.length > LIMITS.pattern))
            found.patterns = `Each pattern can be up to ${LIMITS.pattern} characters`;
    }
    const allowMax = rule.trigger === "preset" ? LIMITS.presetAllow : LIMITS.allow;
    if (rule.allowList.length > allowMax) found.allowList = `Up to ${allowMax} words`;
    else if (rule.allowList.some((word) => word.length > LIMITS.keyword)) found.allowList = `Each word can be up to ${LIMITS.keyword} characters`;
    if (rule.trigger === "preset" && !rule.presets.length) found.presets = "Pick at least one list";
    if (rule.trigger === "mention_spam" && !whole(rule.mentionLimit, 1, LIMITS.mentions)) found.mentionLimit = `Pick 1 to ${LIMITS.mentions}`;
    if ((rule.blockMessage ?? "").length > LIMITS.message) found.blockMessage = `Up to ${LIMITS.message} characters`;
    const acts = rule.trigger === "member_profile" ? rule.blockInteraction : rule.block;
    if (!acts && !rule.alertChannelId && !rule.timeoutSeconds) found.actions = "Pick at least one thing to do";
    return found;
}

const NATIVE_FIELDS = [
    "name",
    "enabled",
    "keywords",
    "patterns",
    "allowList",
    "presets",
    "mentionLimit",
    "raidProtection",
    "block",
    "blockMessage",
    "alertChannelId",
    "timeoutSeconds",
    "blockInteraction",
    "exemptRoleIds",
    "exemptChannelIds",
] as const;

export function nativeChanges(saved: NativeRule, draft: NativeRule): NativeRulePatch {
    const patch: Record<string, unknown> = {};
    for (const field of NATIVE_FIELDS) {
        let value: unknown = draft[field];
        if (field === "blockMessage") value = draft.blockMessage?.trim() || null;
        if (field === "name") value = draft.name.trim();
        if (!sameJson(value, saved[field])) patch[field] = value;
    }
    return patch as NativeRulePatch;
}

export const lines = (text: string) => [
    ...new Set(
        text
            .split("\n")
            .map((line) => line.trim())
            .filter(Boolean),
    ),
];
