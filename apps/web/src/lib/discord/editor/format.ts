import { EditorSelection, type EditorState, type SelectionRange, type Text } from "@codemirror/state";
import type { EditorView } from "@codemirror/view";

export const FORMATS = {
    bold: "**",
    italic: "*",
    underline: "__",
    strike: "~~",
    spoiler: "||",
    code: "`",
} as const;

export type Format = keyof typeof FORMATS | "quote";

function run(doc: Text, at: number, step: -1 | 1, char: string) {
    let count = 0;
    for (let pos = step < 0 ? at - 1 : at; pos >= 0 && pos < doc.length && doc.sliceString(pos, pos + 1) === char; pos += step) count += 1;
    return count;
}

function wrapping(doc: Text, range: SelectionRange, marker: string): "outside" | "inside" | null {
    const size = marker.length;
    // An odd run, so * inside ** reads as bold, while *** is both
    const lone = (left: number, right: number) => marker !== "*" || (left % 2 === 1 && right % 2 === 1);
    if (
        doc.sliceString(range.from - size, range.from) === marker &&
        doc.sliceString(range.to, range.to + size) === marker &&
        lone(run(doc, range.from, -1, "*"), run(doc, range.to, 1, "*"))
    )
        return "outside";
    const text = doc.sliceString(range.from, range.to);
    if (text.length > size * 2 && text.startsWith(marker) && text.endsWith(marker)) {
        const left = run(doc, range.from, 1, "*");
        const right = run(doc, range.to, -1, "*");
        if (lone(left, right)) return "inside";
    }
    return null;
}

const quoted = (state: EditorState, range: SelectionRange) => {
    const first = state.doc.lineAt(range.from).number;
    const last = state.doc.lineAt(range.to).number;
    for (let number = first; number <= last; number += 1) if (!/^> ?/.test(state.doc.line(number).text)) return false;
    return true;
};

export function active(state: EditorState): Set<Format> {
    const range = state.selection.main;
    const on = new Set<Format>();
    for (const [format, marker] of Object.entries(FORMATS)) if (wrapping(state.doc, range, marker)) on.add(format as Format);
    if (quoted(state, range)) on.add("quote");
    return on;
}

function toggleQuote(view: EditorView) {
    const { state } = view;
    const unquote = state.selection.ranges.every((range) => quoted(state, range));
    const changes: { from: number; to?: number; insert?: string }[] = [];
    const seen = new Set<number>();
    for (const range of state.selection.ranges) {
        for (let number = state.doc.lineAt(range.from).number; number <= state.doc.lineAt(range.to).number; number += 1) {
            if (seen.has(number)) continue;
            seen.add(number);
            const line = state.doc.line(number);
            if (unquote) changes.push({ from: line.from, to: line.from + (/^> ?/.exec(line.text)?.[0].length ?? 0) });
            else changes.push({ from: line.from, insert: "> " });
        }
    }
    view.dispatch({ changes, scrollIntoView: true, userEvent: "input.format" });
}

export function toggle(view: EditorView, format: Format) {
    if (view.state.readOnly) return false;
    if (format === "quote") toggleQuote(view);
    else {
        const marker = FORMATS[format];
        const size = marker.length;
        view.dispatch(
            view.state.changeByRange((range) => {
                const wrap = wrapping(view.state.doc, range, marker);
                if (wrap === "outside")
                    return {
                        changes: [
                            { from: range.from - size, to: range.from },
                            { from: range.to, to: range.to + size },
                        ],
                        range: EditorSelection.range(range.from - size, range.to - size),
                    };
                if (wrap === "inside")
                    return {
                        changes: [
                            { from: range.from, to: range.from + size },
                            { from: range.to - size, to: range.to },
                        ],
                        range: EditorSelection.range(range.from, range.to - size * 2),
                    };
                return {
                    changes: [
                        { from: range.from, insert: marker },
                        { from: range.to, insert: marker },
                    ],
                    range: EditorSelection.range(range.from + size, range.to + size),
                };
            }),
            { scrollIntoView: true, userEvent: "input.format" },
        );
    }
    view.focus();
    return true;
}
