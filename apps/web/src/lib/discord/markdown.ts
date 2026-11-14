// Discord's markdown as a tree, so it's drawn with elements and never as an HTML string built from what people typed

export type Inline =
    | { type: "text"; text: string }
    | { type: "break" }
    | { type: "bold" | "italic" | "underline" | "strike" | "spoiler"; children: Inline[] }
    | { type: "code"; text: string }
    | { type: "link"; href: string; children: Inline[] }
    | { type: "emoji"; name: string; id: string; animated: boolean }
    | { type: "user" | "role" | "channel"; id: string }
    | { type: "command"; name: string }
    | { type: "time"; at: number; style: string };

export type Block =
    | { type: "paragraph" | "heading1" | "heading2" | "heading3" | "subtext" | "quote" | "item"; children: Inline[] }
    | { type: "codeblock"; text: string }
    | { type: "gap" };

type Rule = { pattern: RegExp; node: (found: RegExpExecArray) => Inline | null };

const wrap = (type: "bold" | "italic" | "underline" | "strike" | "spoiler") => (found: RegExpExecArray) => ({ type, children: inline(found[1]) });

function link(href: string, label: string | null): Inline | null {
    if (!URL.canParse(href) || !/^https?:$/.test(new URL(href).protocol)) return null;
    return { type: "link", href, children: label === null ? [{ type: "text", text: href }] : inline(label) };
}

// Earlier rules win when two start at the same place
const RULES: Rule[] = [
    { pattern: /`([^`\n]+)`/g, node: (found) => ({ type: "code", text: found[1] }) },
    { pattern: /<(a?):(\w+):(\d+)>/g, node: (found) => ({ type: "emoji", name: found[2], id: found[3], animated: found[1] === "a" }) },
    { pattern: /<@&(\d+)>/g, node: (found) => ({ type: "role", id: found[1] }) },
    { pattern: /<@!?(\d+)>/g, node: (found) => ({ type: "user", id: found[1] }) },
    { pattern: /<#(\d+)>/g, node: (found) => ({ type: "channel", id: found[1] }) },
    { pattern: /<\/([\w-]+(?: [\w-]+){0,2}):\d+>/g, node: (found) => ({ type: "command", name: found[1] }) },
    { pattern: /<t:(-?\d+)(?::([tTdDfFsSR]))?>/g, node: (found) => ({ type: "time", at: Number(found[1]) * 1000, style: found[2] ?? "f" }) },
    { pattern: /\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, node: (found) => link(found[2], found[1]) },
    { pattern: /<(https?:\/\/[^\s>]+)>/g, node: (found) => link(found[1], null) },
    { pattern: /https?:\/\/[^\s<]+[^\s<.,:;"')\]]/g, node: (found) => link(found[0], null) },
    { pattern: /\*\*(.+?)\*\*(?!\*)/g, node: wrap("bold") },
    { pattern: /__(.+?)__(?!_)/g, node: wrap("underline") },
    { pattern: /(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\*)/g, node: wrap("italic") },
    { pattern: /(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])/g, node: wrap("italic") },
    { pattern: /~~(.+?)~~/g, node: wrap("strike") },
    { pattern: /\|\|(.+?)\|\|/g, node: wrap("spoiler") },
];

export function inline(text: string): Inline[] {
    const nodes: Inline[] = [];
    let position = 0;
    const push = (plain: string) => {
        const last = nodes.at(-1);
        if (last?.type === "text") last.text += plain;
        else if (plain) nodes.push({ type: "text", text: plain });
    };
    while (position < text.length) {
        let first: { found: RegExpExecArray; rule: Rule } | null = null;
        for (const rule of RULES) {
            rule.pattern.lastIndex = position;
            const found = rule.pattern.exec(text);
            if (found && (!first || found.index < first.found.index)) first = { found, rule };
        }
        if (!first) break;
        const node = first.rule.node(first.found);
        const end = first.found.index + first.found[0].length;
        push(text.slice(position, first.found.index));
        if (node) nodes.push(node);
        else push(first.found[0]);
        position = end;
    }
    push(text.slice(position));
    return nodes;
}

const CODE_BLOCK = /```(?:[\w+-]+\n)?([\s\S]*?)```/g;
const LINES: [RegExp, Exclude<Block["type"], "codeblock" | "gap" | "paragraph">][] = [
    [/^# (.+)/, "heading1"],
    [/^## (.+)/, "heading2"],
    [/^### (.+)/, "heading3"],
    [/^-# (.+)/, "subtext"],
    [/^> ?(.*)/, "quote"],
    [/^\s*[-*] (.+)/, "item"],
];

function lines(text: string, blocks: Block[]) {
    for (const line of text.split("\n")) {
        const last = blocks.at(-1);
        const special = LINES.find(([pattern]) => pattern.test(line));
        if (special) {
            const children = inline(special[0].exec(line)![1]);
            if (special[1] === "quote" && last?.type === "quote") last.children.push({ type: "break" }, ...children);
            else blocks.push({ type: special[1], children });
        } else if (!line.trim()) {
            blocks.push({ type: "gap" });
        } else if (last?.type === "paragraph") {
            last.children.push({ type: "break" }, ...inline(line));
        } else {
            blocks.push({ type: "paragraph", children: inline(line) });
        }
    }
}

const cache = new Map<string, Block[]>();

export function parse(content: string): Block[] {
    const known = cache.get(content);
    if (known) return known;
    const blocks: Block[] = [];
    let position = 0;
    for (const found of content.matchAll(CODE_BLOCK)) {
        const before = content.slice(position, found.index).replace(/\n$/, "");
        if (before) lines(before, blocks);
        blocks.push({ type: "codeblock", text: found[1].replace(/^\n+|\n+$/g, "") });
        position = found.index + found[0].length;
    }
    const rest = content.slice(position).replace(/^\n/, "");
    if (rest || !blocks.length) lines(rest, blocks);
    if (cache.size > 2000) cache.clear();
    cache.set(content, blocks);
    return blocks;
}

const ONLY_EMOJI = /^[\p{Extended_Pictographic}\p{Emoji_Component}\s]*$/u;
const JUMBO_LIMIT = 30;

export function jumbo(blocks: Block[]) {
    if (blocks.length !== 1 || blocks[0].type !== "paragraph") return false;
    let count = 0;
    for (const node of blocks[0].children) {
        if (node.type === "emoji") count += 1;
        else if (node.type === "text" && ONLY_EMOJI.test(node.text)) count += [...node.text.matchAll(/\p{Extended_Pictographic}/gu)].length;
        else if (node.type !== "break") return false;
    }
    return count > 0 && count <= JUMBO_LIMIT;
}

const format = (options: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat(undefined, options);
const CLOCK = format({ hour: "numeric", minute: "2-digit" });
const NUMERIC_DATE: Intl.DateTimeFormatOptions = { year: "numeric", month: "2-digit", day: "2-digit" };
const SHORT_DATE = format(NUMERIC_DATE);
const LONG_DATE = format({ dateStyle: "long" });
const FULL = format({ dateStyle: "full", timeStyle: "short" });
const STYLES: Record<string, Intl.DateTimeFormat> = {
    t: CLOCK,
    T: format({ timeStyle: "medium" }),
    d: SHORT_DATE,
    D: LONG_DATE,
    f: format({ dateStyle: "long", timeStyle: "short" }),
    F: FULL,
    s: format({ ...NUMERIC_DATE, hour: "numeric", minute: "2-digit" }),
    S: format({ ...NUMERIC_DATE, hour: "numeric", minute: "2-digit", second: "2-digit" }),
};
const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31_536_000],
    ["month", 2_592_000],
    ["day", 86_400],
    ["hour", 3600],
    ["minute", 60],
    ["second", 1],
];
const RELATIVE = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

function relative(at: number) {
    const seconds = (at - Date.now()) / 1000;
    const [unit, size] = UNITS.find(([, size]) => Math.abs(seconds) >= size) ?? UNITS.at(-1)!;
    return RELATIVE.format(Math.round(seconds / size), unit);
}

export const timestamp = (at: number, style: string) => (style === "R" ? relative(at) : (STYLES[style] ?? STYLES.f).format(at));
export const clock = (at: number) => CLOCK.format(at);
export const fullTime = (at: number) => FULL.format(at);
export const longDate = (at: number) => LONG_DATE.format(at);
export const sameDay = (a: number, b: number) => new Date(a).toDateString() === new Date(b).toDateString();

export function calendar(at: number) {
    const days = Math.round((new Date().setHours(0, 0, 0, 0) - new Date(at).setHours(0, 0, 0, 0)) / 86_400_000);
    if (days === 0) return `Today at ${CLOCK.format(at)}`;
    if (days === 1) return `Yesterday at ${CLOCK.format(at)}`;
    return `${SHORT_DATE.format(at)}, ${CLOCK.format(at)}`;
}

export function fileSize(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}
