<script lang="ts">
    import DiscordEmoji from "#lib/components/discord/DiscordEmoji.svelte";
    import type { TranscriptReaction } from "@square/api-client";

    let { reactions }: { reactions: TranscriptReaction[] } = $props();
</script>

<div class="flex flex-wrap gap-1 pt-1">
    {#each reactions as reaction, index (index)}
        <span class="flex items-center gap-1.5 rounded-lg border border-dc-border bg-dc-surface px-1.5 py-0.5 text-sm font-semibold text-dc-text">
            <DiscordEmoji {...reaction.emoji} class="size-4" />{reaction.count}
        </span>
    {/each}
</div>
