<script lang="ts">
    import type { Snippet } from "svelte";
    import type { ClassValue } from "svelte/elements";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";

    let {
        channel,
        topic,
        spaced = true,
        class: className,
        aside,
        footer,
        children,
    }: {
        channel: string;
        topic?: string;
        spaced?: boolean;
        class?: ClassValue;
        aside?: Snippet;
        footer?: Snippet;
        children: Snippet;
    } = $props();
</script>

<div class={["w-full overflow-hidden rounded-2xl bg-dc-bg text-base leading-5.5 text-dc-text shadow-2xl shadow-black/40", className]}>
    <div class="flex h-12 items-center gap-2 border-b border-dc-line px-4">
        <MaterialSymbolsTagRounded aria-hidden="true" class="size-6 shrink-0 text-dc-muted" />
        <span class="truncate font-semibold text-dc-strong">{channel}</span>
        {#if topic}
            <span aria-hidden="true" class="size-1 shrink-0 rounded-full bg-dc-muted"></span>
            <span class="min-w-0 flex-1 truncate text-sm font-medium text-dc-muted">{topic}</span>
        {/if}
        {#if aside}<div class="ml-auto flex shrink-0 items-center gap-2 text-sm font-medium text-dc-muted">{@render aside()}</div>{/if}
    </div>
    <div class={["flex flex-col pt-4 pb-6", spaced && "gap-4.25"]}>{@render children()}</div>
    {#if footer}<div class="border-t border-dc-line px-4 py-3">{@render footer()}</div>{/if}
</div>
