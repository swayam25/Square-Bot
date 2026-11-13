<script lang="ts">
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Cover from "#lib/components/ui/Cover.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import type { Track } from "@square/api-client";
    import type { Snippet } from "svelte";

    // Spans only, so a row can sit inside a button
    let { track, trailing }: { track: Track; trailing?: Snippet } = $props();
</script>

<Cover src={track.artworkUrl} lazy class="size-12 rounded-xl" />
<span class="flex min-w-0 flex-1 flex-col">
    <span class="truncate text-sm font-semibold">{track.title}</span>
    <span class="flex min-w-0 items-center gap-2 text-xs text-gray-400">
        <span class="truncate">{track.author}</span>
        {#if track.requester}
            <span aria-hidden="true">·</span>
            <Tooltip lazy content="Requested by {track.requester.name}" class="max-w-[50%] min-w-0 shrink-0">
                <span class="flex min-w-0 items-center gap-1">
                    <Avatar src={track.requester.avatarUrl} name={track.requester.name} class="size-4 text-[0.5rem]" />
                    <span class="truncate">{track.requester.name}</span>
                </span>
            </Tooltip>
        {/if}
    </span>
</span>
{#if trailing}{@render trailing()}{/if}
