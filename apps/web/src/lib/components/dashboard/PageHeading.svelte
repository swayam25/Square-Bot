<script lang="ts">
    import Seo from "#lib/components/site/Seo.svelte";
    import type { Snippet } from "svelte";

    let { title, description, actions }: { title: string; description?: string; actions?: Snippet } = $props();
</script>

<Seo {title} {description} />

<header class="@container">
    <div class="flex flex-col gap-4 @2xl:flex-row @2xl:items-end @2xl:justify-between">
        <div class="flex min-w-0 flex-col gap-2">
            <h1 class="font-display text-3xl font-semibold tracking-tight wrap-anywhere">{title}</h1>
            {#if description}<p class="text-gray-400">{description}</p>{/if}
        </div>
        {#if actions}<div class="flex shrink-0 flex-wrap gap-2">{@render actions()}</div>{/if}
    </div>
</header>
