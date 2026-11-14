<script lang="ts">
    import DiscordTooltip from "#lib/components/discord/DiscordTooltip.svelte";
    import type { ClassValue } from "svelte/elements";

    let {
        name,
        id = "",
        animated = false,
        class: className = "size-[1.375em]",
    }: { name: string; id?: string; animated?: boolean; class?: ClassValue } = $props();
</script>

{#if id}
    <DiscordTooltip lazy content=":{name}:" class="shrink-0 align-bottom">
        <img
            src="https://cdn.discordapp.com/emojis/{id}.{animated ? 'gif' : 'webp'}?size=48"
            alt=":{name}:"
            loading="lazy"
            class={["inline-block shrink-0 cursor-pointer object-contain", className]}
        />
    </DiscordTooltip>
{:else}
    <span class="shrink-0">{name}</span>
{/if}
