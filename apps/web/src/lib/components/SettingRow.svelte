<script lang="ts">
    import type { Component, Snippet } from "svelte";

    let {
        label,
        description,
        icon: Icon,
        layout = "side",
        children,
    }: {
        label: string;
        description?: string;
        icon?: Component;
        layout?: "side" | "inline" | "below";
        children?: Snippet;
    } = $props();
</script>

<div
    class={[
        "flex gap-4 p-4",
        layout === "inline" && "items-center",
        layout === "side" && "flex-col md:flex-row md:items-center",
        layout === "below" && "flex-col",
    ]}
>
    <div class="flex min-w-0 flex-1 items-center gap-4">
        {#if Icon}
            <span class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-surface-2 text-accent"><Icon class="size-5" /></span>
        {/if}
        <div class="flex min-w-0 flex-col">
            <span class="text-sm font-medium">{label}</span>
            {#if description}<span class="text-sm text-gray-400">{description}</span>{/if}
        </div>
    </div>
    {#if children}
        <div class={["min-w-0", layout === "side" && "md:w-80 md:shrink-0", layout === "inline" && "shrink-0"]}>{@render children()}</div>
    {/if}
</div>
