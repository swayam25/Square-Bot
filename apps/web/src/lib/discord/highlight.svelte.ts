import type { HLJSApi } from "highlight.js";

// Like Discord, only blocks naming a known language are colored, never guessed
export type CodeToken = { text: string; scope: string | null };

let engine = $state.raw<HLJSApi | null>(null);
let loading: Promise<void> | null = null;

export const highlighter = {
    get ready() {
        return engine !== null;
    },
};

export function loadHighlighter() {
    loading ??= import("highlight.js/lib/common").then((module) => void (engine = module.default)).catch(() => void (loading = null));
    return loading;
}

const ENTITIES: Record<string, string> = { "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#x27;": "'" };
const unescape = (text: string) => text.replace(/&(?:amp|lt|gt|quot|#x27);/g, (entity) => ENTITIES[entity]);

// highlight.js only writes escaped text and <span class> pairs, so this reads it back safely without a DOM
function tokens(html: string): CodeToken[] {
    const out: CodeToken[] = [];
    const scopes: string[] = [];
    for (const part of html.split(/(<span class="[^"]*">|<\/span>)/)) {
        if (part.startsWith("<span")) scopes.push(part.slice(13, -2));
        else if (part === "</span>") scopes.pop();
        else if (part) out.push({ text: unescape(part), scope: scopes.at(-1) ?? null });
    }
    return out;
}

// Not reactive on purpose: it fills during render, where state writes aren't allowed
// eslint-disable-next-line svelte/prefer-svelte-reactivity
const cache = new Map<string, CodeToken[] | null>();

export function highlight(code: string, language: string | undefined): CodeToken[] | null {
    if (!engine || !language || !engine.getLanguage(language)) return null;
    const key = `${language}\n${code}`;
    if (!cache.has(key)) {
        if (cache.size > 200) cache.clear();
        cache.set(key, tokens(engine.highlight(code, { language, ignoreIllegals: true }).value));
    }
    return cache.get(key)!;
}
