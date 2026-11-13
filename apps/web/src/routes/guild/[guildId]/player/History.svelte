<script lang="ts">
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { time } from "#lib/format.ts";
    import * as music from "#lib/music.remote.ts";
    import { SvelteSet } from "svelte/reactivity";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import SvgSpinners90RingWithBg from "~icons/svg-spinners/90-ring-with-bg";
    import { control, locked, type Access } from "./player.ts";
    import TrackRow from "./TrackRow.svelte";

    let { guild, access }: { guild: string; access: Access } = $props();

    const historyQuery = $derived(music.liveHistory(guild));
    const played = $derived(historyQuery.current);
    const lock = $derived(locked(access, { own: true }));

    let busy = new SvelteSet<string>();
    async function replay(index: number, identifier: string) {
        busy.add(identifier);
        await control(music.replayTrack({ guild, index, identifier }), { announce: true });
        busy.delete(identifier);
    }
</script>

<section aria-labelledby="played" class="flex flex-col gap-2">
    <h2 id="played" class="px-2 font-display text-lg font-semibold">
        Played <span class="font-mono text-sm font-normal text-gray-400">{played?.length ?? 0}</span>
    </h2>
    {#if played?.length}
        <ol class="flex flex-col gap-1">
            {#each played as track, index (`${index}:${track.identifier}`)}
                <li class="flex items-center gap-2 rounded-2xl p-2 transition-colors hover:bg-surface-2">
                    <TrackRow {track}>
                        {#snippet trailing()}
                            <span class="shrink-0 pr-1 font-mono text-xs text-gray-400">{track.isStream ? "Live" : time(track.lengthMs)}</span>
                            <Tooltip content={lock ?? "Add to the queue again"}>
                                <button
                                    type="button"
                                    aria-busy={busy.has(track.identifier)}
                                    disabled={!!lock || busy.has(track.identifier)}
                                    class="flex size-8 shrink-0 items-center justify-center rounded-full text-gray-300 transition-colors hover:bg-surface-3 hover:text-gray-50 disabled:opacity-40"
                                    onclick={() => replay(index, track.identifier)}
                                >
                                    {#if busy.has(track.identifier)}<SvgSpinners90RingWithBg class="size-4" />{:else}<MaterialSymbolsAddRounded
                                            class="size-5"
                                        />{/if}
                                </button>
                            </Tooltip>
                        {/snippet}
                    </TrackRow>
                </li>
            {/each}
        </ol>
    {:else if historyQuery.error}
        <EmptyState
            tone="danger"
            compact
            title="Couldn't load the history"
            text={historyQuery.error.message ?? "Square didn't answer. Try again in a moment."}
            retry={() => historyQuery.reconnect()}
        />
    {:else if played}
        <p class="px-2 text-sm text-gray-400">Songs played in this session show up here.</p>
    {/if}
</section>
