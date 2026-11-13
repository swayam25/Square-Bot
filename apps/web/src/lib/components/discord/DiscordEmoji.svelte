<script lang="ts">
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import type { ClassValue } from "svelte/elements";

    let {
        name,
        id = "",
        animated = false,
        class: className = "size-[1.375em]",
    }: { name: string; id?: string; animated?: boolean; class?: ClassValue } = $props();
</script>

{#if id}
    <Tooltip lazy content=":{name}:" class="shrink-0 align-bottom">
        <img
            src="https://cdn.discordapp.com/emojis/{id}.{animated ? 'gif' : 'webp'}?size=48"
            alt=":{name}:"
            loading="lazy"
            class={["inline-block shrink-0 object-contain", className]}
        />
    </Tooltip>
{:else}
    <span class="shrink-0">{name}</span>
{/if}
