<script lang="ts">
    import DiscordTooltip from "#lib/components/discord/DiscordTooltip.svelte";
    import type { ClassValue } from "svelte/elements";

    let {
        name,
        id = "",
        animated = false,
        tooltip = true,
        class: className = "size-[1.375em]",
    }: { name: string; id?: string; animated?: boolean; tooltip?: boolean; class?: ClassValue } = $props();
</script>

{#snippet image(extra: ClassValue)}
    <img
        src="https://cdn.discordapp.com/emojis/{id}.{animated ? 'gif' : 'webp'}?size=48"
        alt=":{name}:"
        loading="lazy"
        class={["inline-block shrink-0 object-contain", extra, className]}
    />
{/snippet}

<!-- Discord names an emoji on hover only in message text, never on buttons -->
{#if id && tooltip}
    <DiscordTooltip lazy content=":{name}:" class="shrink-0 align-bottom">{@render image("cursor-pointer")}</DiscordTooltip>
{:else if id}
    {@render image("align-bottom")}
{:else}
    <span class={["@container-size inline-grid shrink-0 place-items-center", className]}>
        <span class="font-emoji text-[100cqh] leading-none">{name}</span>
    </span>
{/if}
