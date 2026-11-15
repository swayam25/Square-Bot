import type { EmojiData, GroupKey, UnicodeEmoji } from "#lib/emoji.ts";
import { forGuild, read } from "#lib/server/bot.ts";
import { prerender, query } from "$app/server";
import * as sdk from "@square/api-client";
import data from "emojibase-data/en/data.json";
import shortcodes from "emojibase-data/en/shortcodes/iamcal.json";
import { z } from "zod";

// Twemoji.woff2 is built from Twemoji 17, so newer emoji would draw as empty boxes
const FONT_EMOJI_VERSION = 17;

const SOURCE_GROUPS: Record<GroupKey, number> = {
    smileys: 0,
    people: 1,
    nature: 3,
    food: 4,
    travel: 5,
    activities: 6,
    objects: 7,
    symbols: 8,
    flags: 9,
};

export const guildEmojis = query(z.string().regex(/^\d{17,20}$/), (guild) => read(sdk.guildEmojis(forGuild(guild))));

export const emojiData = prerender((): EmojiData => {
    const groups = Object.fromEntries(Object.keys(SOURCE_GROUPS).map((key) => [key, [] as UnicodeEmoji[]])) as EmojiData;
    const keys = new Map(Object.entries(SOURCE_GROUPS).map(([key, group]) => [group, key as GroupKey]));

    for (const emoji of data.toSorted((a, b) => (a.order ?? 0) - (b.order ?? 0))) {
        const group = emoji.group === undefined ? undefined : keys.get(emoji.group);
        if (!group || emoji.version > FONT_EMOJI_VERSION) continue;

        const codes = [shortcodes[emoji.hexcode] ?? []].flat();
        const terms = [emoji.label, ...(emoji.tags ?? []), ...codes].join(" ").toLowerCase();
        const skins = (emoji.skins ?? [])
            .filter((skin) => typeof skin.tone === "number" && skin.version <= FONT_EMOJI_VERSION)
            .toSorted((a, b) => Number(a.tone) - Number(b.tone))
            .map((skin) => skin.emoji);

        const entry: UnicodeEmoji = [emoji.emoji, emoji.label, codes[0] ?? emoji.label.toLowerCase().replaceAll(/\W+/g, "_"), terms];
        if (skins.length === 5) entry.push(skins);
        groups[group].push(entry);
    }
    return groups;
});
