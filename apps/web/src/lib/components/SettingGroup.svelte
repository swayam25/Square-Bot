<script lang="ts">
    import type { Snippet } from "svelte";

    let { title, description, actions, children }: { title?: string; description?: string; actions?: Snippet; children: Snippet } = $props();
</script>

<section class="flex flex-col gap-2">
    {#if title || actions}
        <div class="flex flex-wrap items-end gap-4 px-2">
            <div class="flex min-w-60 flex-1 flex-col">
                {#if title}<h2 class="font-display text-lg font-semibold">{title}</h2>{/if}
                {#if description}<p class="text-sm text-gray-400">{description}</p>{/if}
            </div>
            {#if actions}<div class="flex shrink-0 gap-2">{@render actions()}</div>{/if}
        </div>
    {/if}
    <div class="flex flex-col divide-y divide-white/5 rounded-3xl bg-gray-900">{@render children()}</div>
</section>
