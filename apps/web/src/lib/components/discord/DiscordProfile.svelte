<script lang="ts">
    import DiscordMarkdown from "#lib/components/discord/DiscordMarkdown.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Picture from "#lib/components/ui/Picture.svelte";
    import type { ClassValue } from "svelte/elements";

    let {
        name,
        avatar,
        banner,
        color,
        bio,
        class: className,
    }: { name: string; avatar: string | null; banner: string | null; color: string | null; bio: string | null; class?: ClassValue } = $props();
</script>

<div
    data-discord
    class={["w-full overflow-hidden rounded-card bg-dc-surface text-base leading-5.5 text-dc-text shadow-2xl shadow-black/40", className]}
>
    <div class="relative">
        {#if banner}
            <Picture src={banner} alt="" animate class="flex aspect-5/2 w-full">
                {#snippet fallback({ loading })}<span class={["size-full", loading && "skeleton"]}></span>{/snippet}
            </Picture>
        {:else}
            <div class="h-26 bg-dc-border" style:background-color={color ?? undefined}></div>
        {/if}
        <span class="absolute -bottom-10 left-4 flex rounded-full bg-dc-surface p-1.5">
            <Avatar src={avatar} {name} animate round class="size-20" />
        </span>
    </div>
    <div class="flex flex-col gap-3 px-4 pt-14 pb-4">
        <div class="flex items-center gap-1">
            <span class="truncate text-xl leading-6 font-bold text-dc-strong">{name}</span>
            <span class="shrink-0 rounded bg-dc-blurple px-1 text-2xs leading-3.75 font-semibold text-white">APP</span>
        </div>
        {#if bio}
            <DiscordMarkdown text={bio} jumbo={false} />
        {/if}
    </div>
</div>
