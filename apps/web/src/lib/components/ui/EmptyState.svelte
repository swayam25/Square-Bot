<script lang="ts">
    import Button from "#lib/components/ui/Button.svelte";
    import type { Component } from "svelte";
    import type { ClassValue } from "svelte/elements";
    import MaterialSymbolsErrorRounded from "~icons/material-symbols/error-rounded";
    import MaterialSymbolsRefreshRounded from "~icons/material-symbols/refresh-rounded";

    let {
        icon,
        title,
        text,
        tone = "muted",
        retry,
        compact = false,
        card = false,
        class: className,
    }: {
        icon?: Component;
        title: string;
        text?: string;
        tone?: "muted" | "danger";
        retry?: () => unknown;
        compact?: boolean;
        card?: boolean;
        class?: ClassValue;
    } = $props();

    const Icon = $derived(icon ?? MaterialSymbolsErrorRounded);
    let retrying = $state(false);

    async function again() {
        retrying = true;
        try {
            await retry?.();
        } finally {
            retrying = false;
        }
    }
</script>

<div
    role={tone === "danger" ? "alert" : undefined}
    class={[
        "flex flex-1 flex-col items-center justify-center text-center",
        compact ? "gap-1 p-4" : "gap-2 p-8",
        card && "rounded-3xl bg-surface-1",
        card && (compact ? "min-h-48" : "min-h-80"),
        className,
    ]}
>
    <span
        class={[
            "flex shrink-0 items-center justify-center",
            compact ? "mb-2 size-10 rounded-xl" : "mb-2 size-14 rounded-2xl",
            tone === "danger" ? "bg-red-400/10 text-red-400" : "bg-surface-2 text-gray-100",
        ]}
    >
        <Icon class={compact ? "size-5" : "size-7"} />
    </span>
    <p class={["font-display font-semibold", compact ? "text-base" : "text-lg"]}>{title}</p>
    {#if text}<p class="max-w-sm text-sm text-gray-400">{text}</p>{/if}
    {#if retry}
        <Button size="sm" class="mt-2" loading={retrying} onclick={again}>
            {#if !retrying}<MaterialSymbolsRefreshRounded />{/if}{retrying ? "Trying…" : "Try again"}
        </Button>
    {/if}
</div>
