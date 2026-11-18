import type { Tone } from "#lib/components/ui/Chip.svelte";
import { relative } from "#lib/format.ts";
import type { Giveaway, GiveawayCreate, GiveawayPatch, Person } from "@square/api-client";

export type GiveawayStatus = Giveaway["status"];

export const IMAGE_TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp"];
export const IMAGE_MAX_BYTES = 8 * 1024 * 1024;
export const LIMITS = { prize: 256, description: 2000, text: 3000, label: 40, winners: 50, roles: 10, entries: 100, days: 3650, invites: 10_000 };
const MIN_LENGTH = 10_000;
const YEAR = 365 * 24 * 60 * 60 * 1000;

export type Style = Giveaway["buttonStyle"];
export const STYLES: { value: Style; label: string }[] = [
    { value: "blurple", label: "Blurple" },
    { value: "green", label: "Green" },
    { value: "grey", label: "Grey" },
    { value: "red", label: "Red" },
];

export const statusName: Record<GiveawayStatus, string> = { scheduled: "Scheduled", running: "Running", ended: "Ended" };
export const statusTone: Record<GiveawayStatus, Tone> = { scheduled: "warning", running: "success", ended: "muted" };

export type BonusDraft = { key: number; roleId: string | null; entries: number | null };

export type Draft = {
    channelId: string | null;
    prize: string;
    description: string;
    winnerCount: number | null;
    startNow: boolean;
    startsAt: number | null;
    endsAt: number | null;
    host: Person | null;
    requiredRoleIds: string[];
    requireAllRoles: boolean;
    blockedRoleIds: string[];
    minAccountDays: number | null;
    minMemberDays: number | null;
    minInvites: number | null;
    bonusRoles: BonusDraft[];
    pingRoleId: string | null;
    winnerRoleId: string | null;
    color: string | null;
    imageUrl: string;
    imageFile: string | null;
    imageUpload: { name: string; dataUrl: string } | null;
    buttonLabel: string;
    buttonEmoji: string | null;
    buttonStyle: Style;
};

let keys = 0;
export const bonusRow = (roleId: string | null = null, entries: number | null = 1): BonusDraft => ({ key: ++keys, roleId, entries });

const HOUR = 60 * 60 * 1000;
export function roundedHour(from = Date.now()) {
    const date = new Date(from);
    const whole = date.getMinutes() === 0 && date.getSeconds() === 0 && date.getMilliseconds() === 0;
    return new Date(date.getFullYear(), date.getMonth(), date.getDate(), date.getHours() + (whole ? 0 : 1)).getTime();
}

export function blankDraft(): Draft {
    return {
        channelId: null,
        prize: "",
        description: "",
        winnerCount: 1,
        startNow: true,
        startsAt: null,
        endsAt: roundedHour() + 24 * HOUR,
        host: null,
        requiredRoleIds: [],
        requireAllRoles: false,
        blockedRoleIds: [],
        minAccountDays: 0,
        minMemberDays: 0,
        minInvites: 0,
        bonusRoles: [],
        pingRoleId: null,
        winnerRoleId: null,
        color: null,
        imageUrl: "",
        imageFile: null,
        imageUpload: null,
        buttonLabel: "Enter",
        buttonEmoji: null,
        buttonStyle: "blurple",
    };
}

export function draftOf(giveaway: Giveaway): Draft {
    return {
        channelId: giveaway.channelId,
        prize: giveaway.prize,
        description: giveaway.description,
        winnerCount: giveaway.winnerCount,
        startNow: false,
        startsAt: giveaway.startsAt,
        endsAt: giveaway.endsAt,
        host: giveaway.host,
        requiredRoleIds: giveaway.requiredRoleIds,
        requireAllRoles: giveaway.requireAllRoles,
        blockedRoleIds: giveaway.blockedRoleIds,
        minAccountDays: giveaway.minAccountDays,
        minMemberDays: giveaway.minMemberDays,
        minInvites: giveaway.minInvites,
        bonusRoles: giveaway.bonusRoles.map((entry) => bonusRow(entry.roleId, entry.entries)),
        pingRoleId: giveaway.pingRoleId,
        winnerRoleId: giveaway.winnerRoleId,
        color: giveaway.color,
        imageUrl: giveaway.imageUrl ?? "",
        imageFile: giveaway.imageFile,
        imageUpload: null,
        buttonLabel: giveaway.buttonLabel,
        buttonEmoji: giveaway.buttonEmoji,
        buttonStyle: giveaway.buttonStyle,
    };
}

const whole = (value: number | null, min: number, max: number) => Number.isInteger(value) && value! >= min && value! <= max;
export const validUrl = (url: string) => /^https:\/\/\S+$/.test(url.trim()) && url.trim().length <= 2048;

export type Problems = Partial<Record<keyof Draft | "bonus", string>>;

export function problemsOf(draft: Draft, status: GiveawayStatus | "new", now: number): Problems {
    const problems: Problems = {};
    if (!draft.channelId) problems.channelId = "Pick a channel";
    if (!draft.prize.trim()) problems.prize = "Name the prize";
    if (draft.prize.trim().length + draft.description.trim().length > LIMITS.text) {
        problems.description = `The prize and description can add up to ${LIMITS.text.toLocaleString("en")} characters`;
    }
    if (!whole(draft.winnerCount, 1, LIMITS.winners)) problems.winnerCount = `Pick 1 to ${LIMITS.winners} winners`;
    const scheduled = status === "new" ? !draft.startNow : status === "scheduled";
    const starts = scheduled && draft.startsAt !== null ? Math.max(draft.startsAt, now) : now;
    if (scheduled && draft.startsAt === null) problems.startsAt = "Pick when it starts";
    else if (scheduled && draft.startsAt! - now > YEAR) problems.startsAt = "Schedule it up to a year ahead";
    if (status !== "ended") {
        if (draft.endsAt === null) problems.endsAt = "Pick when it ends";
        else if (draft.endsAt - starts < MIN_LENGTH) problems.endsAt = scheduled ? "End it after it starts" : "Pick a time in the future";
        else if (draft.endsAt - starts > YEAR) problems.endsAt = "A giveaway can run for up to a year";
    }
    if (!whole(draft.minAccountDays, 0, LIMITS.days)) problems.minAccountDays = `Pick 0 to ${LIMITS.days} days`;
    if (!whole(draft.minMemberDays, 0, LIMITS.days)) problems.minMemberDays = `Pick 0 to ${LIMITS.days} days`;
    if (!whole(draft.minInvites, 0, LIMITS.invites)) problems.minInvites = `Pick 0 to ${LIMITS.invites.toLocaleString("en")} invites`;
    const bonusIds = draft.bonusRoles.map((entry) => entry.roleId);
    if (draft.bonusRoles.some((entry) => !entry.roleId)) problems.bonus = "Pick a role for every bonus";
    else if (new Set(bonusIds).size !== bonusIds.length) problems.bonus = "Each role can only get one bonus";
    else if (draft.bonusRoles.some((entry) => !whole(entry.entries, 1, LIMITS.entries)))
        problems.bonus = `Bonus entries go from 1 to ${LIMITS.entries}`;
    const linked = !draft.imageUpload && !draft.imageFile;
    if (linked && draft.imageUrl.trim() && !validUrl(draft.imageUrl)) problems.imageUrl = "Use a full link starting with https://";
    return problems;
}

export function createBody(draft: Draft): GiveawayCreate {
    return {
        channelId: draft.channelId!,
        prize: draft.prize.trim(),
        description: draft.description.trim(),
        winnerCount: draft.winnerCount!,
        startsAt: draft.startNow ? null : draft.startsAt,
        endsAt: draft.endsAt!,
        hostId: draft.host?.id ?? null,
        requiredRoleIds: draft.requiredRoleIds,
        requireAllRoles: draft.requireAllRoles,
        blockedRoleIds: draft.blockedRoleIds,
        minAccountDays: draft.minAccountDays!,
        minMemberDays: draft.minMemberDays!,
        minInvites: draft.minInvites!,
        bonusRoles: draft.bonusRoles.map((entry) => ({ roleId: entry.roleId!, entries: entry.entries! })),
        pingRoleId: draft.pingRoleId,
        winnerRoleId: draft.winnerRoleId,
        color: draft.color,
        imageUrl: draft.imageUpload || draft.imageFile ? null : draft.imageUrl.trim() || null,
        imageData: draft.imageUpload?.dataUrl ?? null,
        buttonLabel: draft.buttonLabel.trim(),
        buttonEmoji: draft.buttonEmoji,
        buttonStyle: draft.buttonStyle,
    };
}

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

export function patchBody(draft: Draft, saved: Giveaway): GiveawayPatch {
    const next = createBody({ ...draft, startNow: false });
    const was = createBody({ ...draftOf(saved), startNow: false });
    const changes: Record<string, unknown> = {};
    for (const key of Object.keys(next) as (keyof GiveawayCreate)[]) {
        if (!same(next[key], was[key])) changes[key] = next[key];
    }
    if (changes.hostId === null) delete changes.hostId;
    delete changes.imageData;
    delete changes.imageUrl;
    if (draft.imageUpload) changes.imageData = draft.imageUpload.dataUrl;
    else if (!draft.imageFile) {
        const link = draft.imageUrl.trim() || null;
        if (saved.imageFile || link !== saved.imageUrl) changes.imageUrl = link;
    }
    return changes as GiveawayPatch;
}

export const lockedOnceEnded = new Set<keyof Draft | "bonus">([
    "channelId",
    "startsAt",
    "endsAt",
    "winnerCount",
    "requiredRoleIds",
    "requireAllRoles",
    "blockedRoleIds",
    "minAccountDays",
    "minMemberDays",
    "minInvites",
    "bonusRoles",
    "bonus",
    "pingRoleId",
    "winnerRoleId",
]);

export function whenText(entry: { status: GiveawayStatus; startsAt: number; endsAt: number; endedAt: number | null }, now: number) {
    if (entry.status === "scheduled") return `Starts ${relative(entry.startsAt, now)}`;
    if (entry.status === "running") return `Ends ${relative(entry.endsAt, now)}`;
    return `Ended ${relative(entry.endedAt ?? entry.endsAt, now)}`;
}
