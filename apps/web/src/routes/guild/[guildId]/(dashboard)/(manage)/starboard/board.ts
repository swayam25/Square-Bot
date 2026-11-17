import type { Starboard, StarboardPatch } from "@square/api-client";

export const LIMITS = { boards: 5, emojis: 5, votes: 1000, channels: 50, roles: 25 };

export const AGES = [
    { value: "any", label: "Any age", days: null },
    { value: "1", label: "1 day", days: 1 },
    { value: "3", label: "3 days", days: 3 },
    { value: "7", label: "1 week", days: 7 },
    { value: "14", label: "2 weeks", days: 14 },
    { value: "30", label: "1 month", days: 30 },
    { value: "90", label: "3 months", days: 90 },
    { value: "365", label: "1 year", days: 365 },
];

export type Draft = {
    channelId: string;
    enabled: boolean;
    emojis: string[];
    downvoteEmojis: string[];
    threshold: number | null;
    // Kept apart from the number, so turning removal off and on again remembers it
    dropOn: boolean;
    dropBelow: number | null;
    selfVote: boolean;
    allowBots: boolean;
    channelMode: Starboard["channelMode"];
    channelIds: string[];
    blockedRoleIds: string[];
    maxAgeDays: number | null;
    followDeletes: boolean;
    color: string | null;
};

export function fromBoard(board: Starboard): Draft {
    return {
        channelId: board.channelId,
        enabled: board.enabled,
        emojis: [...board.emojis],
        downvoteEmojis: [...board.downvoteEmojis],
        threshold: board.threshold,
        dropOn: board.dropBelow !== null,
        dropBelow: board.dropBelow ?? 1,
        selfVote: board.selfVote,
        allowBots: board.allowBots,
        channelMode: board.channelMode,
        channelIds: [...board.channelIds],
        blockedRoleIds: [...board.blockedRoleIds],
        maxAgeDays: board.maxAgeDays,
        followDeletes: board.followDeletes,
        color: board.color,
    };
}

function toBody(draft: Draft): Required<StarboardPatch> {
    return {
        channelId: draft.channelId,
        enabled: draft.enabled,
        emojis: draft.emojis,
        downvoteEmojis: draft.downvoteEmojis,
        threshold: draft.threshold ?? 0,
        dropBelow: draft.dropOn ? draft.dropBelow : null,
        selfVote: draft.selfVote,
        allowBots: draft.allowBots,
        channelMode: draft.channelMode,
        channelIds: draft.channelMode === "all" ? [] : draft.channelIds,
        blockedRoleIds: draft.blockedRoleIds,
        maxAgeDays: draft.maxAgeDays,
        followDeletes: draft.followDeletes,
        color: draft.color,
    };
}

export function changes(board: Starboard, draft: Draft): StarboardPatch {
    const before = toBody(fromBoard(board));
    const after = toBody(draft);
    return Object.fromEntries(
        Object.entries(after).filter(([key, value]) => JSON.stringify(value) !== JSON.stringify(before[key as keyof StarboardPatch])),
    );
}

export type Problems = Partial<Record<"emojis" | "downvoteEmojis" | "threshold" | "dropBelow", string>>;

const votes = (value: number | null) => value !== null && Number.isInteger(value) && value >= 1 && value <= LIMITS.votes;
const key = (emoji: string) => /:(\d{17,20})>$/.exec(emoji)?.[1] ?? emoji.replaceAll("️", "");

export function problems(draft: Draft): Problems {
    const found: Problems = {};
    if (!draft.emojis.length) found.emojis = "Add at least one vote emoji";
    const up = new Set(draft.emojis.map(key));
    if (draft.downvoteEmojis.some((emoji) => up.has(key(emoji)))) found.downvoteEmojis = "An emoji can't be a vote and a downvote";
    if (!votes(draft.threshold)) found.threshold = `Pick 1 to ${LIMITS.votes}`;
    if (draft.dropOn) {
        if (!votes(draft.dropBelow)) found.dropBelow = `Pick 1 to ${LIMITS.votes}`;
        else if (votes(draft.threshold) && draft.dropBelow! > draft.threshold!) found.dropBelow = "Can't be more than the votes needed";
    }
    return found;
}
