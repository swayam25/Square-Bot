import DiscordEmoji from "#lib/components/discord/DiscordEmoji.svelte";
import Mention from "#lib/components/discord/Mention.svelte";
import FormatBar from "#lib/components/fields/FormatBar.svelte";
import OverlayScrollbar from "#lib/components/ui/OverlayScrollbar.svelte";
import { channelSource, emojiByName, emojiSource, mentionSource, renderVisual, warmEmojis } from "#lib/discord/editor/completions.ts";
import { active, toggle, type Format } from "#lib/discord/editor/format.ts";
import type { GuildLookups } from "#lib/discord/guild.svelte.ts";
import { highlight, highlighter, loadHighlighter } from "#lib/discord/highlight.svelte.ts";
import { CODE_BLOCK, EMOJI, LINES, spans, timestamp, type Span } from "#lib/discord/markdown.ts";
import { acceptCompletion, autocompletion, selectedCompletionIndex, setSelectedCompletion } from "@codemirror/autocomplete";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { EditorState, Prec, StateEffect, StateField, type Extension, type Range } from "@codemirror/state";
import {
    Decoration,
    EditorView,
    keymap,
    showTooltip,
    tooltips,
    ViewPlugin,
    WidgetType,
    type DecorationSet,
    type Tooltip,
    type TooltipView,
} from "@codemirror/view";
import { mount, unmount } from "svelte";

type Mounted = ReturnType<typeof mount>;
const mounted = new WeakMap<HTMLElement, Mounted>();

// Kept while its key matches, so the mounted component updates names in place
class MountWidget extends WidgetType {
    constructor(
        readonly key: string,
        readonly draw: (target: HTMLElement) => Mounted,
    ) {
        super();
    }
    eq(other: MountWidget) {
        return other.key === this.key;
    }
    toDOM() {
        const dom = document.createElement("span");
        mounted.set(dom, this.draw(dom));
        return dom;
    }
    destroy(dom: HTMLElement) {
        const instance = mounted.get(dom);
        if (instance) void unmount(instance);
    }
    ignoreEvent() {
        return false;
    }
}

class TimeWidget extends WidgetType {
    constructor(
        readonly at: number,
        readonly style: string,
    ) {
        super();
    }
    eq(other: TimeWidget) {
        return other.at === this.at && other.style === this.style;
    }
    toDOM() {
        const dom = document.createElement("time");
        dom.className = "rounded-[3px] bg-white/6 px-0.5";
        dom.textContent = timestamp(this.at, this.style);
        return dom;
    }
    ignoreEvent() {
        return false;
    }
}

const MARKS: Partial<Record<Span["type"], string>> = {
    bold: "font-bold",
    italic: "italic",
    underline: "underline",
    strike: "line-through",
    spoiler: "rounded-sm bg-black/40",
    code: "rounded-sm bg-black/30 font-mono text-[0.85em] [font-variant-ligatures:none]",
    link: "text-dc-link",
    everyone: "rounded-[3px] bg-dc-blurple/30 px-0.5 font-medium text-dc-mention",
};

const LINE_CLASSES: Record<(typeof LINES)[number][1], string> = {
    heading1: "text-xl font-bold",
    heading2: "text-lg font-bold",
    heading3: "text-base font-bold",
    subtext: "text-xs text-gray-400",
    quote: "border-l-4 border-gray-600 pl-2",
    item: "",
};

const syntax = Decoration.mark({ class: "text-gray-500" });
const codeLine = Decoration.line({ class: "bg-black/30 font-mono [font-variant-ligatures:none]" });

function widgetFor(span: Span, lookups: GuildLookups): WidgetType | null {
    const [, first, second, third] = span.found;
    switch (span.type) {
        case "user":
            return new MountWidget(`user:${first}`, (target) =>
                mount(Mention, {
                    target,
                    props: {
                        kind: "user",
                        get name() {
                            return lookups.user(first)?.name ?? "unknown-user";
                        },
                    },
                }),
            );
        case "role":
            return new MountWidget(`role:${first}`, (target) =>
                mount(Mention, {
                    target,
                    props: {
                        kind: "role",
                        get name() {
                            return lookups.role(first)?.name ?? "unknown-role";
                        },
                        get color() {
                            return lookups.role(first)?.color || null;
                        },
                    },
                }),
            );
        case "channel":
            return new MountWidget(`channel:${first}`, (target) =>
                mount(Mention, {
                    target,
                    props: {
                        get kind() {
                            return lookups.channel(first)?.voice ? ("voice" as const) : ("channel" as const);
                        },
                        get name() {
                            return lookups.channel(first)?.name ?? "unknown-channel";
                        },
                        get guild() {
                            return lookups.channel(first)?.guild;
                        },
                    },
                }),
            );
        case "command":
            return new MountWidget(`command:${first}`, (target) => mount(Mention, { target, props: { kind: "command", name: first } }));
        case "emoji":
            return new MountWidget(`emoji:${third}`, (target) =>
                mount(DiscordEmoji, { target, props: { name: second, id: third, animated: first === "a", tooltip: false, class: EMOJI } }),
            );
        case "time":
            return new TimeWidget(Number(first) * 1000, second ?? "f");
        default:
            return null;
    }
}

type Drawn = { all: DecorationSet; atomic: DecorationSet };

function draw(state: EditorState, lookups: GuildLookups): Drawn {
    const text = state.doc.toString();
    const all: Range<Decoration>[] = [];
    const atomic: Range<Decoration>[] = [];
    const fenced: [number, number][] = [];

    for (const found of text.matchAll(CODE_BLOCK)) {
        const from = found.index;
        const to = from + found[0].length;
        fenced.push([from, to]);
        for (let line = state.doc.lineAt(from); ; line = state.doc.line(line.number + 1)) {
            all.push(codeLine.range(line.from));
            if (line.to >= to || line.number === state.doc.lines) break;
        }
        all.push(syntax.range(from, from + 3), syntax.range(to - 3, to));
        const [, language, code] = found;
        const tokens = highlight(code, language?.toLowerCase());
        let at = from + 3 + (language ? language.length + 1 : 0);
        for (const token of tokens ?? []) {
            if (token.scope && token.text) all.push(Decoration.mark({ class: token.scope }).range(at, at + token.text.length));
            at += token.text.length;
        }
    }

    for (let number = 1; number <= state.doc.lines; number += 1) {
        const line = state.doc.line(number);
        if (fenced.some(([from, to]) => line.from >= from && line.to <= to)) continue;
        let body = line.text;
        let offset = line.from;
        const special = LINES.find(([pattern]) => pattern.test(line.text));
        if (special) {
            const content = special[0].exec(line.text)![1];
            const start = line.text.length - content.length;
            if (LINE_CLASSES[special[1]]) all.push(Decoration.line({ class: LINE_CLASSES[special[1]] }).range(line.from));
            if (start > 0) all.push(syntax.range(line.from, line.from + start));
            body = content;
            offset = line.from + start;
        }
        for (const span of spans(body, offset)) {
            const widget = widgetFor(span, lookups);
            if (widget) {
                const replace = Decoration.replace({ widget }).range(span.from, span.to);
                all.push(replace);
                atomic.push(replace);
                continue;
            }
            const style = MARKS[span.type];
            if (span.inner) {
                all.push(syntax.range(span.from, span.from + span.inner), syntax.range(span.to - span.inner, span.to));
                if (style && span.to - span.inner > span.from + span.inner)
                    all.push(Decoration.mark({ class: style }).range(span.from + span.inner, span.to - span.inner));
            } else if (style) {
                all.push(Decoration.mark({ class: style }).range(span.from, span.to));
            }
        }
    }
    return { all: Decoration.set(all, true), atomic: Decoration.set(atomic, true) };
}

const codeReady = StateEffect.define<null>();
const NAMED_FENCE = /```[\w+-]+\n/;

const codeHighlighting = ViewPlugin.fromClass(
    class {
        gone = false;
        constructor(readonly view: EditorView) {
            this.check();
        }
        update() {
            this.check();
        }
        check() {
            if (highlighter.ready || !NAMED_FENCE.test(this.view.state.doc.toString())) return;
            void loadHighlighter().then(() => {
                if (!this.gone && highlighter.ready) this.view.dispatch({ effects: codeReady.of(null) });
            });
        }
        destroy() {
            this.gone = true;
        }
    },
);

function decorations(lookups: GuildLookups) {
    return StateField.define<Drawn>({
        create: (state) => draw(state, lookups),
        update: (drawn, transaction) =>
            transaction.docChanged || transaction.effects.some((effect) => effect.is(codeReady)) ? draw(transaction.state, lookups) : drawn,
        provide: (field) => [
            EditorView.decorations.from(field, (drawn) => drawn.all),
            // Mentions and emojis move and delete as one unit, like in Discord
            EditorView.atomicRanges.of((view) => view.state.field(field).atomic),
        ],
    });
}

const setFocused = StateEffect.define<boolean>();
const setPressing = StateEffect.define<boolean>();

const pointer = StateField.define({
    create: () => ({ focused: false, pressing: false }),
    update(value, transaction) {
        for (const effect of transaction.effects) {
            if (effect.is(setFocused)) value = { ...value, focused: effect.value };
            if (effect.is(setPressing)) value = { ...value, pressing: effect.value };
        }
        return value;
    },
});

// Waits for the drag to end instead of chasing the pointer
function formatBar(touch: boolean): Extension {
    const create = (view: EditorView): TooltipView => {
        const dom = document.createElement("div");
        const props = $state({ active: active(view.state) });
        const instance = mount(FormatBar, {
            target: dom,
            props: {
                get active() {
                    return props.active;
                },
                onformat: (format: Format) => toggle(view, format),
            },
        });
        return {
            dom,
            update: (update) => {
                if (update.docChanged || update.selectionSet) props.active = active(update.state);
            },
            destroy: () => void unmount(instance),
        };
    };
    return [
        pointer,
        EditorView.focusChangeEffect.of((_, focusing) => setFocused.of(focusing)),
        EditorView.domEventHandlers({
            pointerdown(event, view) {
                if (event.button !== 0) return;
                view.dispatch({ effects: setPressing.of(true) });
                const release = () => view.dispatch({ effects: setPressing.of(false) });
                window.addEventListener("pointerup", release, { once: true });
                window.addEventListener("pointercancel", release, { once: true });
            },
        }),
        showTooltip.compute([pointer, "selection"], (state): Tooltip | null => {
            const { focused, pressing } = state.field(pointer);
            const range = state.selection.main;
            if (!focused || pressing || range.empty || state.readOnly) return null;
            // Below on touch screens, where the system's copy menu sits above
            return { pos: range.from, end: range.to, above: !touch, strictSide: false, create };
        }),
    ];
}

const shortcut = (format: Format) => (view: EditorView) => toggle(view, format);

const SHORTCODE = /(?<![\w<]):([\w+-]{2,32}):/g;

function emojiShortcodes(guild: () => string) {
    return EditorView.inputHandler.of((view, from, to, text) => {
        if (!text.includes(":") || text.includes("\n")) return false;
        warmEmojis(guild());
        // Fast typing can arrive as one change like "l: ", so any :name: it closes is swapped
        const line = view.state.doc.lineAt(from);
        const head = line.text.slice(0, from - line.from);
        const tail = line.text.slice(to - line.from);
        const next = head + text + tail;
        let result = "";
        let last = 0;
        for (const found of next.matchAll(SHORTCODE)) {
            const close = found.index + found[0].length - 1;
            const emoji = close >= head.length && close < head.length + text.length && emojiByName(guild(), found[1]);
            if (!emoji) continue;
            result += next.slice(last, found.index) + emoji;
            last = found.index + found[0].length;
        }
        if (!last) return false;
        result += next.slice(last);
        view.dispatch({
            changes: { from: line.from, to: line.to, insert: result },
            selection: { anchor: line.from + result.length - tail.length },
            userEvent: "input.type",
        });
        return true;
    });
}

// CodeMirror's own list, given the site's overlay scrollbar and hover highlight
function suggestionList(name: string) {
    return ViewPlugin.fromClass(
        class {
            shown: { tooltip: HTMLElement; props: { viewport: HTMLElement | null }; instance: Mounted } | null = null;
            constructor(readonly view: EditorView) {}
            update() {
                this.view.requestMeasure({
                    key: this,
                    read: () => document.querySelector<HTMLElement>(`.${name}`),
                    write: (tooltip) => this.sync(tooltip),
                });
            }
            sync(tooltip: HTMLElement | null) {
                if (this.shown && this.shown.tooltip !== tooltip) this.destroy();
                if (!tooltip) return;
                const viewport = tooltip.querySelector("ul");
                if (this.shown) {
                    this.shown.props.viewport = viewport;
                    return;
                }
                const props = $state({ viewport });
                const instance = mount(OverlayScrollbar, {
                    target: tooltip,
                    props: {
                        get viewport() {
                            return props.viewport;
                        },
                        inset: 8,
                    },
                });
                tooltip.addEventListener("pointermove", (event) => {
                    if (event.pointerType !== "mouse") return;
                    const index = Number(/-(\d+)$/.exec((event.target as Element).closest("li")?.id ?? "")?.[1] ?? NaN);
                    if (!Number.isNaN(index) && index !== selectedCompletionIndex(this.view.state))
                        this.view.dispatch({ effects: setSelectedCompletion(index) });
                });
                this.shown = { tooltip, props, instance };
            }
            destroy() {
                if (this.shown) void unmount(this.shown.instance);
                this.shown = null;
            }
        },
    );
}

const theme = EditorView.theme(
    {
        "&": { fontSize: "inherit" },
        "&.cm-focused": { outline: "none" },
        ".cm-scroller": { fontFamily: "inherit", lineHeight: "1.375rem" },
        ".cm-content": { padding: "0", minHeight: "4.125rem", caretColor: "var(--color-accent)" },
        ".cm-line": { padding: "0" },
        ".cm-placeholder": { color: "var(--color-gray-400)" },
        ".cm-tooltip": { border: "none", backgroundColor: "transparent", zIndex: "200" },
        ".cm-tooltip.cm-tooltip-autocomplete": {
            overflow: "hidden",
            borderRadius: "1rem",
            backgroundColor: "var(--color-gray-800)",
            boxShadow: "0 25px 50px -12px rgb(0 0 0 / 0.5)",
        },
        ".cm-tooltip.cm-tooltip-autocomplete > ul": {
            fontFamily: "inherit",
            padding: "0.5rem",
            maxHeight: "18rem",
            minWidth: "16rem",
            maxWidth: "min(24rem, calc(100vw - 2rem))",
            overscrollBehavior: "contain",
        },
        ".cm-tooltip.cm-tooltip-autocomplete > ul > li": {
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            height: "2.5rem",
            padding: "0 0.75rem",
            borderRadius: "0.75rem",
            fontSize: "0.875rem",
            fontWeight: "500",
            lineHeight: "1.25rem",
            color: "var(--color-gray-100)",
        },
        ".cm-tooltip.cm-tooltip-autocomplete > ul > li[aria-selected]": { backgroundColor: "rgb(255 255 255 / 0.1)", color: "var(--color-gray-100)" },
        ".cm-tooltip.cm-tooltip-autocomplete > ul > completion-section": {
            display: "block",
            padding: "0.5rem 0.75rem 0.25rem",
            border: "none",
            fontSize: "0.75rem",
            fontWeight: "600",
            color: "var(--color-gray-400)",
            opacity: "1",
        },
        ".cm-completionLabel": { flex: "1", minWidth: "0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
        ".cm-completionDetail": {
            marginLeft: "auto",
            fontStyle: "normal",
            fontWeight: "400",
            fontSize: "0.75rem",
            color: "var(--color-gray-400)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
        },
    },
    { dark: true },
);

export type EditorOptions = {
    guild: () => string;
    lookups: GuildLookups;
    touch: boolean;
    onchange: (text: string) => void;
    onblur?: () => void;
};

let editors = 0;

export function discordEditor({ guild, lookups, touch, onchange, onblur }: EditorOptions): Extension {
    const suggestions = `discord-suggestions-${(editors += 1)}`;
    return [
        theme,
        EditorView.lineWrapping,
        history(),
        tooltips({ parent: document.body }),
        decorations(lookups),
        codeHighlighting,
        formatBar(touch),
        emojiShortcodes(guild),
        suggestionList(suggestions),
        autocompletion({
            override: [mentionSource(guild), channelSource(guild), emojiSource(guild)],
            icons: false,
            tooltipClass: () => suggestions,
            maxRenderedOptions: 30,
            addToOptions: [{ render: renderVisual, position: 20 }],
        }),
        Prec.high(
            keymap.of([
                { key: "Tab", run: acceptCompletion },
                { key: "Mod-b", run: shortcut("bold") },
                { key: "Mod-i", run: shortcut("italic") },
                { key: "Mod-u", run: shortcut("underline") },
            ]),
        ),
        keymap.of([...historyKeymap, ...defaultKeymap]),
        EditorView.updateListener.of((update) => {
            if (update.docChanged) onchange(update.state.doc.toString());
            if (update.focusChanged && update.view.hasFocus) warmEmojis(guild());
            if (update.focusChanged && !update.view.hasFocus) onblur?.();
        }),
    ];
}

// Over the limit, an edit is refused unless it shortens the text
export const maxLength = (max: number) =>
    EditorState.transactionFilter.of((transaction) =>
        transaction.docChanged && transaction.newDoc.length > max && transaction.newDoc.length > transaction.startState.doc.length ? [] : transaction,
    );
