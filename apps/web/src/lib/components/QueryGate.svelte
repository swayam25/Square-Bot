<script lang="ts">
    import PageHeading from "#lib/components/PageHeading.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import type { Snippet } from "svelte";
    import MaterialSymbolsRefreshRounded from "~icons/material-symbols/refresh-rounded";

    // Shows `children` once every query has a value. `ready` stays true while a query refreshes, so saved pages don't flash.
    let {
        queries,
        title,
        description,
        children,
    }: {
        queries: { ready: boolean; error?: { message?: string } }[];
        title?: string;
        description?: string;
        children: Snippet;
    } = $props();

    const ready = $derived(queries.every((query) => query.ready));
    const failed = $derived(queries.find((query) => query.error)?.error);
</script>

{#if ready}
    {@render children()}
{:else}
    <div class="flex flex-col gap-8">
        {#if title}<PageHeading {title} {description} />{/if}
        {#if failed}
            <div role="alert" class="flex flex-col items-start gap-4 rounded-4xl bg-red-400/10 p-6">
                <p class="text-sm font-medium text-red-400">{failed.message ?? "Square couldn't load this."}</p>
                <Button onclick={() => location.reload()}><MaterialSymbolsRefreshRounded />Try again</Button>
            </div>
        {:else}
            <div aria-hidden="true" class="grid gap-4 lg:grid-cols-2">
                <div class="h-48 animate-pulse rounded-4xl bg-surface-1"></div>
                <div class="h-48 animate-pulse rounded-4xl bg-surface-1"></div>
            </div>
        {/if}
    </div>
{/if}
