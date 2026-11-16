<script lang="ts">
    import EmojiPicker from "#lib/components/fields/EmojiPicker.svelte";
    import FieldError from "#lib/components/ui/FieldError.svelte";
    import { passPress } from "#lib/components/ui/press.ts";
    import { discordEditor, maxLength } from "#lib/discord/editor/editor.svelte.ts";
    import { guildLookups } from "#lib/discord/guild.svelte.ts";
    import { mobile } from "#lib/media.ts";
    import { Compartment, EditorState, Transaction } from "@codemirror/state";
    import { EditorView, placeholder as hint } from "@codemirror/view";
    import { untrack } from "svelte";
    import type { ClassValue } from "svelte/elements";

    // The value stays the raw text Discord gets (<@id>, **bold**). Mentions and emojis are only drawn in place
    let {
        value = $bindable(""),
        guild,
        placeholder,
        maxlength,
        error,
        disabled = false,
        onblur,
        "aria-label": label,
        class: className,
    }: {
        value?: string;
        guild: { id: string; name: string; iconUrl: string | null };
        placeholder?: string;
        maxlength?: number;
        error?: string | null;
        disabled?: boolean;
        onblur?: () => void;
        "aria-label": string;
        class?: ClassValue;
    } = $props();

    const errorId = $props.id();
    const lookups = guildLookups(() => guild.id);
    const settings = new Compartment();
    let view = $state<EditorView | null>(null);

    const configured = () => [
        hint(placeholder ?? ""),
        EditorView.editable.of(!disabled),
        EditorState.readOnly.of(disabled),
        EditorView.contentAttributes.of({
            "aria-label": label,
            ...(error && { "aria-invalid": "true", "aria-describedby": errorId }),
        }),
        maxlength == null ? [] : maxLength(maxlength),
    ];

    const editor = (host: HTMLElement) =>
        untrack(() => {
            const created = new EditorView({
                parent: host,
                state: EditorState.create({
                    doc: value,
                    extensions: [
                        discordEditor({
                            guild: () => guild.id,
                            lookups,
                            touch: mobile.current,
                            onchange: (text) => (value = text),
                            onblur: () => onblur?.(),
                        }),
                        settings.of(configured()),
                    ],
                }),
            });
            view = created;
            return () => {
                view = null;
                created.destroy();
            };
        });

    $effect(() => {
        const next = configured();
        untrack(() => view)?.dispatch({ effects: settings.reconfigure(next) });
    });

    // Outside changes, like a discard, replace the text without an undo step
    $effect(() => {
        const text = value;
        const current = view;
        if (!current || current.state.doc.toString() === text) return;
        current.dispatch({ changes: { from: 0, to: current.state.doc.length, insert: text }, annotations: Transaction.addToHistory.of(false) });
    });

    function insert(text: string) {
        if (!view) return;
        view.dispatch(view.state.replaceSelection(text), { scrollIntoView: true, userEvent: "input" });
        view.focus();
    }
</script>

<div
    data-disabled={disabled || undefined}
    class={[
        "group/field relative flex w-full min-w-0 flex-col rounded-3xl bg-gray-800 text-sm",
        "ring-0 ring-accent/60 transition-[background-color,box-shadow] duration-200 ease-out ring-inset",
        "focus-within:ring-2 hover:bg-gray-700",
        "has-aria-invalid:bg-red-400/10 has-aria-invalid:ring-red-400/40",
        "data-disabled:pointer-events-none data-disabled:opacity-50",
        className,
    ]}
    {@attach passPress(() => view?.contentDOM)}
>
    <div class="min-w-0 px-4 pt-3" {@attach editor}></div>
    <div class="flex items-center gap-2 px-4 pt-2 pb-3">
        <EmojiPicker {guild} placement="top-start" {disabled} triggerClass="-ml-2" onpick={insert} finalFocus={() => view?.contentDOM ?? null} />
        {#if maxlength}
            <span aria-hidden="true" class="ml-auto font-mono text-xs text-gray-400">{value.length}/{maxlength}</span>
        {/if}
    </div>
    <FieldError id={errorId} {error} />
</div>
