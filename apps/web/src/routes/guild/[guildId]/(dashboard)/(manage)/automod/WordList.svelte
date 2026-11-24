<script lang="ts">
    import FieldError from "#lib/components/ui/FieldError.svelte";
    import OverlayScrollbar from "#lib/components/ui/OverlayScrollbar.svelte";
    import { discordField } from "#lib/components/ui/styles.ts";
    import { untrack } from "svelte";
    import { lines, sameJson } from "./automod.ts";

    let {
        values = $bindable(),
        label,
        placeholder,
        max,
        error,
        mono = false,
    }: { values: string[]; label: string; placeholder?: string; max: number; error?: string | null; mono?: boolean } = $props();

    const errorId = $props.id();
    let text = $state(untrack(() => values.join("\n")));
    let box = $state<HTMLTextAreaElement>();

    // Blank lines while typing never reach `values`, so only a change from outside (like Discard) rewrites the text
    $effect.pre(() => {
        const next = values;
        if (!sameJson(lines(untrack(() => text)), next)) text = next.join("\n");
    });
</script>

<div class={discordField}>
    <textarea
        bind:this={box}
        bind:value={text}
        oninput={() => (values = lines(text))}
        aria-label={label}
        aria-invalid={!!error || undefined}
        aria-describedby={error ? errorId : undefined}
        {placeholder}
        rows={3}
        spellcheck="false"
        class={[
            "block field-sizing-content max-h-80 min-h-16.5 w-full resize-none bg-transparent px-4 pt-3 leading-5.5 outline-none placeholder:text-gray-400",
            mono && "font-mono",
        ]}></textarea>
    <OverlayScrollbar viewport={box} />
    <div class="flex px-4 pt-2 pb-3">
        <span aria-hidden="true" class={["ml-auto font-mono text-xs", values.length > max ? "text-red-400" : "text-gray-400"]}>
            {values.length}/{max}
        </span>
    </div>
    <FieldError id={errorId} {error} />
</div>
