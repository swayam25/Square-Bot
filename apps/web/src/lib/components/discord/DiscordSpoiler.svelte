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
        class="cursor-pointer rounded-sm bg-[#2e2e34] text-transparent select-none *:invisible hover:bg-[#36363d]"
        onclick={() => (shown = true)}>{@render children()}</button
    >
{/if}
