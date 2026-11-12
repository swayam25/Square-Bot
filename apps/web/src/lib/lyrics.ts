import type { Lyrics, LyricWord } from "#lib/server/lyrics.ts";

export type SungLine = {
    start: number;
    end: number;
    text: string;
    words: LyricWord[];
    timed: boolean;
    interlude: boolean;
    background?: SungLine;
};

const INTERLUDE_MS = 4500;
const SWEEP_MS_PER_CHAR = 22;
const SWEEP_MIN_MS = 350;
const SWEEP_MAX_MS = 850;
const MIN_SUNG_MS = 1200;
const MS_PER_CHAR = 85;
const SUNG_SHARE = 0.9;
const SLACK = 1.4;

const wordSegmenter = typeof Intl !== "undefined" && "Segmenter" in Intl ? new Intl.Segmenter(undefined, { granularity: "word" }) : null;

function splitWords(text: string) {
    const parts = wordSegmenter ? [...wordSegmenter.segment(text)].map((s) => s.segment) : text.split(/(\s+)/).filter(Boolean);
    const words: string[] = [];
    for (const part of parts) {
        if (/^[\s\p{P}]+$/u.test(part) && words.length > 0) words[words.length - 1] += part;
        else words.push(part);
    }
    return words;
}

function sweepWords(text: string, start: number, span: number): LyricWord[] {
    const end = start + Math.min(span, Math.max(SWEEP_MIN_MS, Math.min(SWEEP_MAX_MS, text.length * SWEEP_MS_PER_CHAR)));
    const parts = splitWords(text);
    const weights = parts.map((p) => Math.max(1, [...p.replace(/\s/gu, "")].length));
    const total = weights.reduce((a, b) => a + b, 0);
    let at = start;
    return parts.map((part, i) => {
        const length = ((end - start) * weights[i]) / total;
        const word = { text: part, start: at, end: at + length };
        at += length;
        return word;
    });
}

const interlude = (start: number, end: number): SungLine => ({ start, end, text: "", words: [], timed: false, interlude: true });

export function sungLines(lyrics: Lyrics, durationMs: number): SungLine[] {
    if (lyrics.sync === "none") return [];
    const sung: SungLine[] = [];
    const main = lyrics.lines.filter((line) => !line.background);
    main.forEach((line, i) => {
        let end = line.end;
        if (lyrics.sync === "line") {
            const next = main[i + 1]?.start ?? (durationMs > line.start ? durationMs : line.start + 6000);
            const gap = next - line.start;
            end =
                line.start + Math.max(Math.min(gap, 300), Math.min(gap * SUNG_SHARE, Math.max(MIN_SUNG_MS, line.text.length * MS_PER_CHAR) * SLACK));
        }
        const words = line.words ?? sweepWords(line.text, line.start, end - line.start);
        sung.push({ start: line.start, end, text: line.text, words, timed: !!line.words, interlude: false });
    });
    for (const bg of lyrics.lines.filter((line) => line.background)) {
        const host = sung.findLast((line) => line.start <= bg.start + 50) ?? sung[0];
        if (host && !host.background) {
            host.background = {
                start: bg.start,
                end: bg.end,
                text: bg.text,
                words: bg.words ?? sweepWords(bg.text, bg.start, bg.end - bg.start),
                timed: !!bg.words,
                interlude: false,
            };
        }
    }

    const lines: SungLine[] = [];
    if (sung[0] && sung[0].start >= INTERLUDE_MS) lines.push(interlude(0, sung[0].start));
    // Lines overlap, so a short one can end inside a longer one: silence starts after the latest
    let silent = 0;
    sung.forEach((line, i) => {
        lines.push(line);
        silent = Math.max(silent, line.end, line.background?.end ?? 0);
        const next = sung[i + 1]?.start ?? (durationMs > silent ? durationMs : silent);
        if (next - silent >= INTERLUDE_MS) lines.push(interlude(silent + (lyrics.sync === "line" ? 500 : 0), next));
    });
    return lines;
}

// Voices overlap: a line runs until it ends and the next has started, so one still being sung stays current
// beside the line that came in over it. A line that ended early holds only while nothing else is sung.
export function linesAt(lines: readonly SungLine[], t: number, lead = 0) {
    const current: number[] = [];
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (t < line.start - lead) break;
        if (t < (lines[i + 1]?.start ?? Infinity) || t < line.end) current.push(i);
    }
    const running = current.filter((i) => t < lines[i].end);
    return running.length ? running : current;
}

export type Glyph = { text: string; start: number; end: number };
export type WordGlyphs = { text: string; tail: string; start: number; end: number; letters: Glyph[] | null };

// Scripts whose letters stand alone. Joining scripts (Arabic, Devanagari...) would lose their shaping split apart,
// and RTL ones their order, so those light up word by word instead.
const SPLITTABLE =
    /^[\p{Script=Latin}\p{Script=Cyrillic}\p{Script=Greek}\p{Script=Armenian}\p{Script=Georgian}\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}\p{Script=Common}\p{Script=Inherited}]+$/u;
const graphemes = typeof Intl !== "undefined" && "Segmenter" in Intl ? new Intl.Segmenter(undefined, { granularity: "grapheme" }) : null;
const OVERLAP = 1.8;
const glyphCache = new WeakMap<SungLine, WordGlyphs[]>();

export function glyphsOf(line: SungLine): WordGlyphs[] {
    const known = glyphCache.get(line);
    if (known) return known;
    const result = line.words.map((w): WordGlyphs => {
        const text = w.text.trimEnd();
        const tail = w.text.slice(text.length);
        if (!text || !SPLITTABLE.test(text)) return { text, tail, start: w.start, end: w.end, letters: null };
        const chars = graphemes ? [...graphemes.segment(text)].map((g) => g.segment) : Array.from(text);
        const span = (w.end - w.start) / chars.length;
        const letters = chars.map((c, i) => {
            const start = w.start + span * i;
            return { text: c, start, end: Math.min(w.end, start + span * OVERLAP) };
        });
        return { text, tail, start: w.start, end: w.end, letters };
    });
    glyphCache.set(line, result);
    return result;
}
