import { load, save } from "#lib/storage.ts";
import type { Emoji as GuildEmoji } from "@square/api-client";

export type { GuildEmoji };

// Shortcodes are space separated, the first being the one shown
export type UnicodeEmoji = [emoji: string, label: string, shortcodes: string, terms: string, skins?: string[]];

export const GROUPS = [
    { key: "smileys", name: "Smileys & emotion" },
    { key: "people", name: "People & body" },
    { key: "nature", name: "Animals & nature" },
    { key: "food", name: "Food & drink" },
    { key: "travel", name: "Travel & places" },
    { key: "activities", name: "Activities" },
    { key: "objects", name: "Objects" },
    { key: "symbols", name: "Symbols" },
    { key: "flags", name: "Flags" },
] as const;

export type GroupKey = (typeof GROUPS)[number]["key"];
export type EmojiData = Record<GroupKey, UnicodeEmoji[]>;

export const TONES = ["✋", "✋🏻", "✋🏼", "✋🏽", "✋🏾", "✋🏿"];
export const TONE_NAMES = ["Default", "Light", "Medium-light", "Medium", "Medium-dark", "Dark"];

export function toned(emoji: UnicodeEmoji, tone: number) {
    return (tone && emoji[4]?.[tone - 1]) || emoji[0];
}

export const shortcodeOf = (emoji: UnicodeEmoji) => emoji[2].split(" ", 1)[0];

// Lower is better, -1 is no match
export function emojiScore(query: string, names: string, label: string, terms: string) {
    const each = names.split(" ");
    if (each.includes(query) || label === query) return 0;
    if (each.some((name) => name.startsWith(query)) || label.startsWith(query)) return 1;
    if (` ${terms}`.includes(` ${query}`)) return 2;
    return terms.includes(query) ? 3 : -1;
}

export function customToken(emoji: Pick<GuildEmoji, "id" | "name" | "animated">) {
    return `<${emoji.animated ? "a" : ""}:${emoji.name}:${emoji.id}>`;
}

export function customUrl(emoji: Pick<GuildEmoji, "id" | "animated">, play = true) {
    return `https://cdn.discordapp.com/emojis/${emoji.id}.webp?size=64${emoji.animated && play ? "&animated=true" : ""}`;
}

const TONE_KEY = "square:emoji-tone";
const RECENT_KEY = "square:emoji-recent";
const RECENT_MAX = 16;

export function loadTone() {
    const tone = Number(load(TONE_KEY));
    return Number.isInteger(tone) && tone >= 0 && tone < TONES.length ? tone : 0;
}

export function saveTone(tone: number) {
    save(TONE_KEY, String(tone));
}

export function loadRecent(): string[] {
    try {
        const recent: unknown = JSON.parse(load(RECENT_KEY) ?? "[]");
        return Array.isArray(recent) ? recent.filter((key) => typeof key === "string").slice(0, RECENT_MAX) : [];
    } catch {
        return [];
    }
}

export function addRecent(recent: string[], key: string) {
    const next = [key, ...recent.filter((other) => other !== key)].slice(0, RECENT_MAX);
    save(RECENT_KEY, JSON.stringify(next));
    return next;
}
