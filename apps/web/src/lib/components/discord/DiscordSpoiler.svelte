<script lang="ts">
    import type { Snippet } from "svelte";

    let { children }: { children: Snippet } = $props();

    let shown = $state(false);
</script>

{#if shown}
    <span class="rounded-sm bg-white/10">{@render children()}</span>
{:else}
    <button
        type="button"
        aria-label="Show spoiler"
        class="cursor-pointer rounded-sm bg-dc-spoiler text-transparent select-none *:invisible hover:bg-dc-spoiler-hover"
        onclick={() => (shown = true)}>{@render children()}</button
    >
{/if}
