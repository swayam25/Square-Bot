<script lang="ts">
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import * as music from "#lib/music.remote.ts";
    import type { PlayerState, SkipVote } from "@square/api-client";
    import MaterialSymbolsSkipNextRounded from "~icons/material-symbols/skip-next-rounded";
    import { control, skipping, type Access } from "./player.ts";

    let { guild, player, vote, access }: { guild: string; player: PlayerState; vote: SkipVote; access: Access } = $props();

    let now = $state(Date.now());
    $effect(() => {
        const timer = setInterval(() => (now = Date.now()), 1000);
        return () => clearInterval(timer);
    });
    const left = $derived(Math.max(0, Math.ceil((vote.endsAt - now) / 1000)));

    const votes = $derived(vote.voterIds.length);
    const skip = $derived(skipping(player, access));

    let busy = $state(false);
    async function press() {
        busy = true;
        await control(music.skipTrack({ guild }), { announce: !skip.now });
        busy = false;
    }
</script>

<section
    aria-label="Skip vote"
    class="flex shrink-0 animate-pop-in flex-wrap items-center gap-x-4 gap-y-3 rounded-3xl bg-surface-1 px-4 py-3 md:px-6"
>
    <div class="flex min-w-0 flex-1 items-center gap-3">
        {#if vote.startedBy}
            <Avatar src={vote.startedBy.avatarUrl} name={vote.startedBy.name} class="size-8 shrink-0 text-xs" />
        {/if}
        <div class="flex min-w-0 flex-col gap-1">
            <p class="truncate text-sm font-semibold">
                {vote.startedBy ? `${vote.startedBy.name} wants to skip` : "Vote to skip"}
                {#if player.track}<span class="font-normal text-mist-400">{player.track.title}</span>{/if}
            </p>
            <div class="flex items-center gap-2 text-xs text-mist-400">
                <span
                    role="meter"
                    aria-label="Votes"
                    aria-valuemin={0}
                    aria-valuemax={vote.needed}
                    aria-valuenow={votes}
                    class="h-1 w-20 overflow-hidden rounded-full bg-white/10"
                >
                    <span
                        class="block h-full rounded-full bg-accent transition-[width] duration-400 ease-spring"
                        style:width="{Math.min(1, votes / Math.max(vote.needed, 1)) * 100}%"
                    ></span>
                </span>
                <span class="font-mono tabular-nums">{votes}/{vote.needed}</span>
                <span aria-hidden="true">·</span>
                <span class="tabular-nums">{left}s left</span>
            </div>
        </div>
    </div>
    <Tooltip content={skip.lock} class="max-sm:w-full">
        <Button variant={skip.now ? "primary" : "secondary"} loading={busy} disabled={!!skip.lock || busy} class="max-sm:w-full" onclick={press}>
            {#if !busy}<MaterialSymbolsSkipNextRounded />{/if}{skip.now ? "Skip now" : skip.voted ? "Voted" : "Vote to skip"}
        </Button>
    </Tooltip>
</section>
