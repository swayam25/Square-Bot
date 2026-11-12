import { redis } from "#lib/server/redis.ts";

// Times are milliseconds. A word's text keeps its trailing space, so joining the words rebuilds the line
export type LyricWord = { text: string; start: number; end: number };
export type LyricLine = { start: number; end: number; text: string; words: LyricWord[] | null; background: boolean };
export type Lyrics = { source: "BetterLyrics" | "LRCLIB"; sync: "word" | "line" | "none"; lines: LyricLine[]; instrumental?: true };

export type LyricsQuery = { title: string; artist: string; durationMs: number };

const TIMEOUT_MS = 5_000;
const HIT_TTL = 7 * 24 * 3600;
const MISS_TTL = 24 * 3600;
// Generic on purpose: nothing about the project or its users goes to third-party services
const USER_AGENT = "Mozilla/5.0 (compatible; lyrics-client/1.0)";

const ENTITIES: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };
const decode = (text: string) =>
    text.replace(/&(#x?[\da-f]+|\w+);/gi, (match, code: string) =>
        code[0] === "#"
            ? String.fromCodePoint(Number.parseInt(code.slice(code[1] === "x" ? 2 : 1), code[1] === "x" ? 16 : 10))
            : (ENTITIES[code] ?? match),
    );

// TTML times come as seconds ("27.395") or clock values ("1:02.300", "1:02:03.4")
function clock(value: string | undefined) {
    if (!value) return 0;
    return Math.round(value.split(":").reduce((total, part) => total * 60 + Number.parseFloat(part), 0) * 1000);
}

const attr = (attrs: string, name: string) => new RegExp(`\\b${name}="([^"]*)"`).exec(attrs)?.[1];

function ttmlWords(markup: string): LyricWord[] {
    return [...markup.matchAll(/<span\b([^>]*)>([^<]*)<\/span>(\s?)/g)].map(([, attrs, text, space]) => ({
        text: decode(text) + space,
        start: clock(attr(attrs, "begin")),
        end: clock(attr(attrs, "end")),
    }));
}

export function parseTtml(ttml: string): Lyrics | null {
    const wordTimed = /itunes:timing="Word"/.test(ttml);
    const lines: LyricLine[] = [];
    for (const [, attrs, inner] of ttml.matchAll(/<p\b([^>]*)>([\s\S]*?)<\/p>/g)) {
        const start = clock(attr(attrs, "begin"));
        const end = clock(attr(attrs, "end"));
        // Backing vocals sit in their own span of word spans; they become a separate, dimmer line
        let main = inner;
        for (const [whole, bgAttrs, bgInner] of inner.matchAll(
            /<span\b([^>]*ttm:role="x-bg"[^>]*)>((?:\s*<span\b[^>]*>[^<]*<\/span>)*\s*)<\/span>/g,
        )) {
            main = main.replace(whole, "");
            const words = ttmlWords(bgInner);
            if (words.length) {
                lines.push({
                    start: clock(attr(bgAttrs, "begin")) || words[0].start,
                    end: clock(attr(bgAttrs, "end")) || words.at(-1)!.end,
                    text: words
                        .map((word) => word.text)
                        .join("")
                        .trim(),
                    words,
                    background: true,
                });
            }
        }
        const words = wordTimed ? ttmlWords(main) : [];
        const text = words.length
            ? words
                  .map((word) => word.text)
                  .join("")
                  .trim()
            : decode(main.replace(/<[^>]+>/g, "")).trim();
        if (text) lines.push({ start, end, text, words: words.length ? words : null, background: false });
    }
    if (!lines.length) return null;
    lines.sort((a, b) => a.start - b.start);
    return { source: "BetterLyrics", sync: lines.some((line) => line.words) ? "word" : "line", lines };
}

export function parseLrc(lrc: string, totalMs: number): LyricLine[] {
    const timed: { start: number; text: string }[] = [];
    for (const row of lrc.split("\n")) {
        const stamps = [...row.matchAll(/\[(\d+):(\d+(?:\.\d+)?)\]/g)];
        const text = row.replace(/\[[^\]]*\]/g, "").trim();
        for (const [, minutes, seconds] of stamps) timed.push({ start: Math.round((Number(minutes) * 60 + Number(seconds)) * 1000), text });
    }
    timed.sort((a, b) => a.start - b.start);
    return timed
        .map((line, index) => ({ ...line, end: timed[index + 1]?.start ?? totalMs, words: null, background: false }))
        .filter((line) => line.text);
}

// LRCLIB's `lyricsfile` is YAML; this reads only the shape it uses: lines with start/end and words with a start
export function parseLyricsfile(yaml: string): LyricLine[] {
    const unquote = (value: string) => {
        const raw = value.trim();
        if (raw.startsWith("'") && raw.endsWith("'")) return raw.slice(1, -1).replaceAll("''", "'");
        if (raw.startsWith('"') && raw.endsWith('"')) return JSON.parse(raw) as string;
        return raw;
    };
    const lines: { text: string; start: number; end: number; words: { text: string; start: number }[] }[] = [];
    let line: (typeof lines)[number] | undefined;
    let word: { text: string; start: number } | undefined;
    for (const row of yaml.split("\n")) {
        let match: RegExpExecArray | null;
        if ((match = /^- text: (.*)$/.exec(row))) {
            line = { text: unquote(match[1]), start: 0, end: 0, words: [] };
            lines.push(line);
            word = undefined;
        } else if (line && (match = /^ {2}- text: (.*)$/.exec(row))) {
            word = { text: unquote(match[1]), start: 0 };
            line.words.push(word);
        } else if (line && (match = /^( {2}| {4})(start_ms|end_ms): (\d+)/.exec(row))) {
            const target = match[1].length === 4 ? word : line;
            if (target && match[2] === "start_ms") target.start = Number(match[3]);
            else if (match[2] === "end_ms" && match[1].length === 2) line.end = Number(match[3]);
        }
    }
    return lines
        .filter((entry) => entry.text.trim())
        .map((entry) => ({
            start: entry.start,
            end: entry.end,
            text: entry.text.trim(),
            words: entry.words.length
                ? entry.words.map((item, index) => ({ text: item.text, start: item.start, end: entry.words[index + 1]?.start ?? entry.end }))
                : null,
            background: false,
        }));
}

// YouTube titles and channel names carry noise that lyric databases don't index
export function cleanQuery({ title, artist, durationMs }: LyricsQuery): LyricsQuery {
    let cleanArtist = artist
        .replace(/\s*-\s*Topic$/i, "")
        .replace(/VEVO$/i, "")
        .trim();
    let cleanTitle = title
        .replace(/\s*[([][^)\]]*\b(official|video|audio|lyrics?|visuali[sz]er|mv|m\/v|hd|4k|remaster(ed)?)\b[^)\]]*[)\]]/gi, "")
        .replace(/\s*\b(ft|feat)\.?\s.*$/i, "")
        .trim();
    // "Artist - Song" uploads from a channel that isn't the artist's own
    const split = /^(.+?)\s+[-–—]\s+(.+)$/.exec(cleanTitle);
    if (split && !cleanTitle.toLowerCase().startsWith(cleanArtist.toLowerCase() + " ")) {
        cleanArtist = split[1].trim();
        cleanTitle = split[2].trim();
    } else if (split && cleanTitle.toLowerCase().startsWith(cleanArtist.toLowerCase())) {
        cleanTitle = split[2].trim();
    }
    return { title: cleanTitle || title, artist: cleanArtist || artist, durationMs };
}

async function getJson(url: string, headers: Record<string, string> = {}) {
    const response = await fetch(url, { headers: { "user-agent": USER_AGENT, ...headers }, signal: AbortSignal.timeout(TIMEOUT_MS) });
    return response.ok ? ((await response.json()) as unknown) : null;
}

async function fromBetterLyrics({ title, artist, durationMs }: LyricsQuery): Promise<Lyrics | null> {
    const params = new URLSearchParams({ s: title, a: artist, d: String(Math.round(durationMs / 1000)) });
    const body = (await getJson(`https://lyrics-api.boidu.dev/getLyrics?${params}`)) as { ttml?: string } | null;
    return body?.ttml ? parseTtml(body.ttml) : null;
}

type LrclibEntry = { duration: number; instrumental: boolean; plainLyrics: string | null; syncedLyrics: string | null; lyricsfile?: string | null };

async function fromLrclib({ title, artist, durationMs }: LyricsQuery): Promise<Lyrics | null> {
    const params = new URLSearchParams({ track_name: title, artist_name: artist });
    const results = ((await getJson(`https://lrclib.net/api/search?${params}`)) as LrclibEntry[] | null) ?? [];
    const seconds = durationMs / 1000;
    const matches = results.filter((entry) => Math.abs(entry.duration - seconds) <= 3);
    const close = matches.filter((entry) => !entry.instrumental);
    if (!close.length && matches.length) return { source: "LRCLIB", sync: "none", lines: [], instrumental: true };
    const best = close.find((entry) => entry.lyricsfile) ?? close.find((entry) => entry.syncedLyrics) ?? close.find((entry) => entry.plainLyrics);
    if (!best) return null;
    if (best.lyricsfile) {
        const lines = parseLyricsfile(best.lyricsfile);
        if (lines.some((line) => line.words)) return { source: "LRCLIB", sync: "word", lines };
    }
    if (best.syncedLyrics) {
        const lines = parseLrc(best.syncedLyrics, durationMs);
        if (lines.length) return { source: "LRCLIB", sync: "line", lines };
    }
    const plain = best.plainLyrics?.split("\n").map((text) => text.trim()) ?? [];
    return plain.some(Boolean)
        ? { source: "LRCLIB", sync: "none", lines: plain.map((text) => ({ start: 0, end: 0, text, words: null, background: false })) }
        : null;
}

export async function findLyrics(query: LyricsQuery): Promise<Lyrics | null> {
    const clean = cleanQuery(query);
    const key = `lyrics:v2:${clean.artist.toLowerCase()}:${clean.title.toLowerCase()}:${Math.round(clean.durationMs / 1000)}`;
    const cached = await redis.get(key).catch(() => null);
    if (cached) return JSON.parse(cached) as Lyrics | null;

    const rank = { word: 2, line: 1, none: 0 } as const;
    let lyrics: Lyrics | null = null;
    // Word timing wins whichever service has it, so a line-only answer still asks the next service
    for (const source of [fromBetterLyrics, fromLrclib]) {
        const found = await source(clean).catch(() => null); // A timeout or a bad reply falls through to the next
        if (found && (!lyrics || rank[found.sync] > rank[lyrics.sync])) lyrics = found;
        if (lyrics?.sync === "word") break;
    }
    await redis.set(key, JSON.stringify(lyrics), { expiration: { type: "EX", value: lyrics ? HIT_TTL : MISS_TTL } }).catch(() => {});
    return lyrics;
}
