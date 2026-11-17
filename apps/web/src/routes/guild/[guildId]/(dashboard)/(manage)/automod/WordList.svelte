<script lang="ts">
    import FieldError from "#lib/components/ui/FieldError.svelte";
    import { formatCount } from "#lib/format.ts";
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

    // Blank lines while typing never reach `values`, so only a change from outside (like Discard) rewrites the text
    $effect.pre(() => {
        const next = values;
        if (!sameJson(lines(untrack(() => text)), next)) text = next.join("\n");
    });
</script>

<div class="group/field relative">
    <textarea
        bind:value={text}
        oninput={() => (values = lines(text))}
        aria-label={label}
        aria-invalid={!!error || undefined}
        aria-describedby={error ? errorId : undefined}
        {placeholder}
        rows={5}
        spellcheck="false"
        class={[
            "block max-h-80 min-h-32 w-full resize-y rounded-control-lg bg-gray-800 px-4 py-3 pb-8 text-sm outline-none placeholder:text-gray-400 md:rounded-2xl md:px-3",
            "ring-0 ring-accent/60 transition-[background-color,box-shadow] duration-200 ease-out ring-inset hover:bg-gray-700 focus:ring-2",
            "aria-[invalid=true]:bg-red-400/10 aria-[invalid=true]:ring-red-400/40",
            mono && "font-mono",
        ]}></textarea>
    <span class={["pointer-events-none absolute right-4 bottom-2 text-xs tabular-nums", values.length > max ? "text-red-400" : "text-gray-400"]}>
        {formatCount(values.length)} / {formatCount(max)}
    </span>
    <FieldError id={errorId} {error} />
</div>
