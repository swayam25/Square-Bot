<script lang="ts">
    import type { Snippet } from "svelte";
    import type { ClassValue } from "svelte/elements";

    let { spoiler = false, class: className, children }: { spoiler?: boolean; class?: ClassValue; children: Snippet } = $props();

    // Covers again whenever `spoiler` turns back on
    let shown = $derived(!spoiler);
</script>

{#if shown}
    {@render children()}
{:else}
    <div class={["relative overflow-hidden", className]}>
        <div inert class="size-full blur-2xl brightness-75 select-none">{@render children()}</div>
        <button type="button" class="absolute inset-0 flex cursor-pointer items-center justify-center bg-black/20" onclick={() => (shown = true)}>
            <span class="rounded-full bg-black/60 px-3 py-1.5 text-[15px] leading-none font-bold tracking-wide text-white">SPOILER</span>
        </button>
    </div>
{/if}
