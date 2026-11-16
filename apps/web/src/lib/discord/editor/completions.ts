import { emojiData, guildEmojis } from "#lib/emoji/emoji.remote.ts";
import { customToken, customUrl, emojiScore, loadTone, shortcodeOf, toned, type GuildEmoji, type UnicodeEmoji } from "#lib/emoji/emoji.ts";
import { guildChannels, guildRoles, searchMembers } from "#lib/settings/settings.remote.ts";
import type { Completion, CompletionContext, CompletionResult } from "@codemirror/autocomplete";
import type { Channel } from "@square/api-client";
import { mount, unmount, type Component } from "svelte";
import MaterialSymbolsCampaignRounded from "~icons/material-symbols/campaign-rounded";
import MaterialSymbolsFolderRounded from "~icons/material-symbols/folder-rounded";
import MaterialSymbolsForumRounded from "~icons/material-symbols/forum-rounded";
import MaterialSymbolsPermMediaRounded from "~icons/material-symbols/perm-media-rounded";
import MaterialSymbolsPodcastsRounded from "~icons/material-symbols/podcasts-rounded";
import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
import MaterialSymbolsVolumeUpRounded from "~icons/material-symbols/volume-up-rounded";

const LIMIT = 10;
const TYPING_PAUSE = 120;

type Visual =
    | { kind: "avatar"; src: string }
    | { kind: "at"; color?: string | null }
    | { kind: "icon"; icon: Component }
    | { kind: "glyph"; text: string }
    | { kind: "image"; src: string };

export type Suggestion = Completion & { visual: Visual };

const CHANNEL_ICONS: Record<Channel["type"], Component> = {
    text: MaterialSymbolsTagRounded,
    news: MaterialSymbolsCampaignRounded,
    voice: MaterialSymbolsVolumeUpRounded,
    stage_voice: MaterialSymbolsPodcastsRounded,
    forum: MaterialSymbolsForumRounded,
    media: MaterialSymbolsPermMediaRounded,
    category: MaterialSymbolsFolderRounded,
};

// CodeMirror drops option rows with no cleanup hook, so rows are plain elements and icon markup is copied once
const iconMarkup = new Map<Component, string>();
function iconHtml(icon: Component) {
    let html = iconMarkup.get(icon);
    if (html === undefined) {
        const host = document.createElement("span");
        const instance = mount(icon, { target: host });
        html = host.innerHTML;
        void unmount(instance);
        iconMarkup.set(icon, html);
    }
    return html;
}

export function renderVisual(completion: Completion) {
    const { visual } = completion as Suggestion;
    const box = document.createElement("span");
    box.className = "grid size-6 shrink-0 place-items-center text-gray-400 [&>svg]:size-5";
    if (visual.kind === "avatar" || visual.kind === "image") {
        const image = document.createElement("img");
        image.src = visual.src;
        image.alt = "";
        image.loading = "lazy";
        image.className = visual.kind === "avatar" ? "size-6 rounded-full object-cover" : "size-6 object-contain";
        box.append(image);
    } else if (visual.kind === "at") {
        box.textContent = "@";
        box.classList.add("text-base", "font-bold");
        if (visual.color) box.style.color = visual.color;
    } else if (visual.kind === "glyph") {
        box.textContent = visual.text;
        box.classList.add("font-emoji", "text-xl", "leading-none");
    } else {
        box.innerHTML = iconHtml(visual.icon);
    }
    return box;
}

// Ranked lists keep their order: CodeMirror sorts by boost, then by label
const ranked = (options: Omit<Suggestion, "boost">[]): Suggestion[] => options.map((option, index) => ({ ...option, boost: 99 - index }));

function rank<T>(items: T[], query: string, names: (item: T) => string[]) {
    if (!query) return items;
    const scored: [number, T][] = [];
    for (const item of items) {
        const values = names(item).map((name) => name.toLowerCase());
        const score = values.some((value) => value.startsWith(query)) ? 0 : values.some((value) => value.includes(query)) ? 1 : -1;
        if (score >= 0) scored.push([score, item]);
    }
    return scored.sort((a, b) => a[0] - b[0]).map(([, item]) => item);
}

// Remote queries are thenables without catch
const settle = <T>(pending: PromiseLike<T>, fallback: T) => Promise.resolve(pending).catch(() => fallback);

const pause = (context: CompletionContext) =>
    new Promise<boolean>((resolve) => {
        const timer = setTimeout(() => resolve(!context.aborted), TYPING_PAUSE);
        context.addEventListener("abort", () => {
            clearTimeout(timer);
            resolve(false);
        });
    });

const SECTIONS = {
    members: { name: "Members", rank: 0 },
    roles: { name: "Roles", rank: 1 },
    channels: { name: "Channels", rank: 0 },
    emojis: { name: "Emojis", rank: 0 },
};

export function mentionSource(guild: () => string) {
    return async (context: CompletionContext): Promise<CompletionResult | null> => {
        const typed = context.matchBefore(/(?<![\w<@&])@[\p{L}\p{N}_.-]{0,32}$/u);
        if (!typed) return null;
        const query = typed.text.slice(1).toLowerCase();
        const id = guild();

        const [members, roles] = await Promise.all([
            query && (await pause(context)) ? settle(searchMembers({ guild: id, q: query }), []) : [],
            settle(guildRoles(id), []),
        ]);
        if (context.aborted) return null;

        const people = members.slice(0, LIMIT).map((user) => ({
            label: user.name,
            detail: user.username,
            apply: `<@${user.id}> `,
            section: SECTIONS.members,
            visual: { kind: "avatar", src: user.avatarUrl } as const,
        }));
        const everyone = ["everyone", "here"]
            .filter((name) => name.startsWith(query))
            .map((name) => ({ label: name, apply: `@${name} `, section: SECTIONS.roles, visual: { kind: "at" } as const }));
        const named = rank(roles, query, (role) => [role.name])
            .slice(0, LIMIT)
            .map((role) => ({
                label: role.name,
                apply: `<@&${role.id}> `,
                section: SECTIONS.roles,
                visual: { kind: "at", color: role.color } as const,
            }));
        const options = ranked([...people, ...named, ...everyone]);
        return options.length ? { from: typed.from, options, filter: false } : null;
    };
}

export function channelSource(guild: () => string) {
    return async (context: CompletionContext): Promise<CompletionResult | null> => {
        const typed = context.matchBefore(/(?<![\w<#&])#[\p{L}\p{N}\p{Extended_Pictographic}_-]{0,100}$/u);
        if (!typed) return null;
        const query = typed.text.slice(1).toLowerCase();
        const channels = await settle(guildChannels(guild()), []);
        if (context.aborted) return null;
        const categories = new Map(channels.filter((channel) => channel.type === "category").map((channel) => [channel.id, channel.name]));
        const options = ranked(
            rank(channels, query, (channel) => [channel.name])
                .slice(0, LIMIT)
                .map((channel) => ({
                    label: channel.name,
                    detail: (channel.parentId && categories.get(channel.parentId)) || undefined,
                    apply: `<#${channel.id}> `,
                    section: SECTIONS.channels,
                    visual: { kind: "icon", icon: CHANNEL_ICONS[channel.type] } as const,
                })),
        );
        return options.length ? { from: typed.from, options, filter: false } : null;
    };
}

let unicode: UnicodeEmoji[] | null = null;
let unicodeLoading: Promise<UnicodeEmoji[]> | null = null;
const customs = new Map<string, GuildEmoji[]>();

async function loadEmojis(guild: string) {
    unicodeLoading ??= settle(emojiData(), null).then((data) => {
        if (!data) unicodeLoading = null;
        return (unicode = data ? Object.values(data).flat() : null) ?? [];
    });
    const [all, own] = await Promise.all([unicodeLoading, settle(guildEmojis(guild), [])]);
    customs.set(guild, own);
    return { all, own: own.filter((emoji) => emoji.usable) };
}

export function warmEmojis(guild: string) {
    if (!unicode || !customs.has(guild)) void loadEmojis(guild);
}

// Null while the emoji lists are still loading
export function emojiByName(guild: string, name: string) {
    const own = customs.get(guild)?.find((emoji) => emoji.usable && emoji.name === name);
    if (own) return customToken(own);
    const found = unicode?.find((emoji) => emoji[2].split(" ").includes(name.toLowerCase()));
    return found ? toned(found, loadTone()) : null;
}

export function emojiSource(guild: () => string) {
    return async (context: CompletionContext): Promise<CompletionResult | null> => {
        const typed = context.matchBefore(/(?<![\w<]):[\w+-]{2,32}$/);
        if (!typed) return null;
        const query = typed.text.slice(1).toLowerCase();
        const { all, own } = await loadEmojis(guild());
        if (context.aborted) return null;

        const scored: [number, Omit<Suggestion, "boost">][] = [];
        for (const emoji of own) {
            const score = emojiScore(query, emoji.name.toLowerCase(), emoji.name.toLowerCase(), emoji.name.toLowerCase());
            if (score >= 0)
                scored.push([
                    score - 0.5,
                    {
                        label: `:${emoji.name}:`,
                        apply: customToken(emoji),
                        section: SECTIONS.emojis,
                        visual: { kind: "image", src: customUrl(emoji, false) },
                    },
                ]);
        }
        const tone = loadTone();
        for (const emoji of all) {
            const score = emojiScore(query, emoji[2], emoji[1].toLowerCase(), emoji[3]);
            if (score >= 0) {
                const glyph = toned(emoji, tone);
                const name = emoji[2].split(" ").find((code) => code.startsWith(query)) ?? shortcodeOf(emoji);
                scored.push([score, { label: `:${name}:`, apply: glyph, section: SECTIONS.emojis, visual: { kind: "glyph", text: glyph } }]);
            }
        }
        const options = ranked(
            scored
                .sort((a, b) => a[0] - b[0])
                .slice(0, LIMIT)
                .map(([, option]) => option),
        );
        return options.length ? { from: typed.from, options, filter: false } : null;
    };
}
