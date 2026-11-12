<script lang="ts">
    import OverlayScrollbar from "#lib/components/ui/OverlayScrollbar.svelte";
    import Segmented from "#lib/components/ui/Segmented.svelte";
    import type { PlayerState, QueueState } from "@square/api-client";
    import type { Component } from "svelte";
    import { cubicOut } from "svelte/easing";
    import { fly } from "svelte/transition";
    import MaterialSymbolsHistoryRounded from "~icons/material-symbols/history-rounded";
    import MaterialSymbolsLyricsRounded from "~icons/material-symbols/lyrics-rounded";
    import MaterialSymbolsQueueMusicRounded from "~icons/material-symbols/queue-music-rounded";
    import MaterialSymbolsSearchRounded from "~icons/material-symbols/search-rounded";
    import History from "./History.svelte";
    import Lyrics from "./Lyrics.svelte";
    import type { Access, Tab } from "./player.ts";
    import Queue from "./Queue.svelte";
    import SearchPanel from "./SearchPanel.svelte";

    let {
        guild,
        player,
        queue,
        position,
        online,
        lyricsOff,
        access,
        tab = $bindable(),
        sheet = false,
    }: {
        guild: string;
        player: PlayerState;
        queue: QueueState | undefined;
        position: number;
        online: boolean;
        lyricsOff: string | false;
        access: Access;
        tab: Tab;
        sheet?: boolean;
    } = $props();

    let queueList = $state<HTMLElement | null>(null);
    let historyList = $state<HTMLElement | null>(null);
    const track = $derived(player.track);
    const ORDER: Tab[] = ["search", "queue", "history", "lyrics"];
    let direction = $state(1);
    function choose(next: Tab) {
        direction = ORDER.indexOf(next) >= ORDER.indexOf(tab) ? 1 : -1;
        tab = next;
    }

    const tabs = $derived<{ value: Tab; label: string; icon: Component; count?: number; disabled?: string | false }[]>([
        { value: "search", label: "Search", icon: MaterialSymbolsSearchRounded },
        { value: "queue", label: "Queue", icon: MaterialSymbolsQueueMusicRounded, count: queue?.total },
        { value: "history", label: "History", icon: MaterialSymbolsHistoryRounded },
        { value: "lyrics", label: "Lyrics", icon: MaterialSymbolsLyricsRounded, disabled: tab === "lyrics" ? false : lyricsOff },
    ]);
</script>

<section
    aria-label="Search, queue, history and lyrics"
    class={[
        "flex flex-col gap-4 overflow-hidden",
        sheet ? "min-h-0 flex-1 pt-2" : "h-144 rounded-3xl bg-surface-1 pt-4 md:pt-6 lg:h-auto lg:min-h-0",
    ]}
>
    {#if !sheet}
        <div class="shrink-0 px-4 md:px-6"><Segmented label="Panel" options={tabs} bind:value={() => tab, choose} /></div>
    {/if}

    {#key tab}
        <div
            role={sheet ? undefined : "tabpanel"}
            class="flex min-h-0 flex-1 flex-col"
            in:fly={{ x: 24 * direction, duration: sheet ? 0 : 300, easing: cubicOut }}
        >
            {#if tab === "search"}
                <SearchPanel {guild} />
            {:else if tab === "queue"}
                <div class="relative min-h-0 flex-1">
                    <div bind:this={queueList} class="size-full overflow-y-auto overscroll-contain px-2 pb-6 md:px-4">
                        {#if queue}<Queue {guild} {queue} {access} autoplay={player.autoplay} />{/if}
                    </div>
                    <OverlayScrollbar viewport={queueList} inset={16} />
                </div>
            {:else if tab === "history"}
                <div class="relative min-h-0 flex-1">
                    <div bind:this={historyList} class="size-full overflow-y-auto overscroll-contain px-2 pb-6 md:px-4">
                        <History {guild} {access} />
                    </div>
                    <OverlayScrollbar viewport={historyList} inset={16} />
                </div>
            {:else if track && !track.isStream}
                {#key track.identifier}
                    <Lyrics {guild} {track} {position} playing={!player.paused && online} />
                {/key}
            {:else}
                <div class="flex flex-1 flex-col items-center justify-center gap-2 p-10 text-center">
                    <span class="mb-2 flex size-14 items-center justify-center rounded-2xl bg-surface-2 text-mist-100">
                        <MaterialSymbolsLyricsRounded class="size-7" />
                    </span>
                    <p class="font-display text-lg font-semibold">No lyrics</p>
                    <p class="text-sm text-mist-400">{lyricsOff || "Lyrics show up while a song plays"}</p>
                </div>
            {/if}
        </div>
    {/key}
</section>
