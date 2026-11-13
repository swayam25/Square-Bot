<script lang="ts">
    import PageHeading from "#lib/components/PageHeading.svelte";
    import PageSkeleton from "#lib/components/PageSkeleton.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import type { Snippet } from "svelte";

    let {
        queries,
        title,
        description,
        actions = false,
        skeleton,
        children,
    }: {
        queries: { ready: boolean; error?: { message?: string }; refresh?: () => Promise<unknown> }[];
        title?: string;
        description?: string;
        actions?: boolean;
        skeleton?: Snippet;
        children: Snippet;
    } = $props();

    const ready = $derived(queries.every((query) => query.ready));
    const failed = $derived(queries.find((query) => query.error)?.error);
</script>

{#snippet actionsSkeleton()}
    <span aria-hidden="true" class="h-12 w-28 skeleton rounded-full md:h-10"></span>
{/snippet}

{#if ready}
    {@render children()}
{:else}
    <div class="flex flex-col gap-6">
        {#if title}
            <PageHeading {title} {description} actions={actions && !failed ? actionsSkeleton : undefined} />
        {/if}
        {#if failed}
            <EmptyState
                tone="danger"
                card
                title="Couldn't load this page"
                text={failed.message ?? "Square didn't answer. Try again in a moment."}
                retry={() => Promise.all(queries.filter((query) => query.error).map((query) => query.refresh?.()))}
            />
        {:else}
            {#if skeleton}{@render skeleton()}{:else}<PageSkeleton />{/if}
        {/if}
    </div>
{/if}
