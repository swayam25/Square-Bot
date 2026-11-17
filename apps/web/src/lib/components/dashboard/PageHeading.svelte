<script lang="ts">
    import Seo from "#lib/components/site/Seo.svelte";
    import type { Snippet } from "svelte";

    let { title, description, actions }: { title: string; description?: string; actions?: Snippet } = $props();
</script>

<Seo {title} {description} />

<header class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
    <div class="flex flex-col gap-2">
        <h1 class="font-display text-3xl font-semibold tracking-tight wrap-anywhere">{title}</h1>
        {#if description}<p class="text-gray-400">{description}</p>{/if}
    </div>
    {#if actions}<div class="flex gap-2">{@render actions()}</div>{/if}
</header>
