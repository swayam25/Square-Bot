<script module lang="ts">
    type Source = "youtube_music" | "youtube" | "spotify" | "apple_music";

    // The ones the Lavalink node answers for; SoundCloud and Deezer came back empty or with errors
    const SOURCES: { value: Source; label: string }[] = [
        { value: "youtube_music", label: "YT Music" },
        { value: "youtube", label: "YouTube" },
        { value: "spotify", label: "Spotify" },
        { value: "apple_music", label: "Apple Music" },
    ];
</script>

<script lang="ts">
    import BrandIcon from "#lib/components/BrandIcon.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import OverlayScrollbar from "#lib/components/ui/OverlayScrollbar.svelte";
    import ScrollRow from "#lib/components/ui/ScrollRow.svelte";
    import { errorMessage } from "#lib/errors.ts";
    import { formatCount, time } from "#lib/format.ts";
    import { ripple } from "#lib/motion.ts";
    import * as music from "#lib/music.remote.ts";
    import type { SearchResults } from "@square/api-client";
    import { SvelteSet } from "svelte/reactivity";
    import MaterialSymbolsPlaylistAddRounded from "~icons/material-symbols/playlist-add-rounded";
    import MaterialSymbolsSearchRounded from "~icons/material-symbols/search-rounded";
    import SvgSpinners90RingWithBg from "~icons/svg-spinners/90-ring-with-bg";
    import { control } from "./player.ts";
    import TrackRow from "./TrackRow.svelte";

    let { guild }: { guild: string } = $props();

    const DEBOUNCE_MS = 450;

    let text = $state("");
    let source = $state<Source>("youtube_music");
    let results = $state.raw<SearchResults | null>(null);
    let searching = $state(false);
    let problem = $state("");
    const adding = new SvelteSet<string>();
    let latest = 0;
    let list = $state<HTMLElement | null>(null);

    async function search() {
        const query = text.trim();
        const ticket = ++latest;
        if (!query) {
            results = null;
            problem = "";
            return;
        }
        searching = true;
        try {
            const found = await music.searchMusic({ guild, query, source });
            // A slower, older search must not overwrite the one the member is looking at
            if (ticket === latest) {
                results = found;
                problem = "";
            }
        } catch (err) {
            if (ticket === latest) problem = errorMessage(err, "Search isn't available right now.");
        } finally {
            if (ticket === latest) searching = false;
        }
    }

    let timer: ReturnType<typeof setTimeout> | undefined;

    // Emptying the box (typing it away or its clear button, which fires no input event) drops the old results
    // right away, and any search still on its way
    $effect(() => {
        if (text.trim()) return;
        clearTimeout(timer);
        latest++;
        results = null;
        problem = "";
        searching = false;
    });
    $effect(() => () => clearTimeout(timer));
    function schedule() {
        clearTimeout(timer);
        timer = setTimeout(search, DEBOUNCE_MS);
    }

    function pick(next: Source) {
        source = next;
        if (text.trim()) void search();
    }

    async function add(key: string, query: string) {
        if (adding.has(key)) return;
        adding.add(key);
        await control(music.playQuery({ guild, query }), { announce: true });
        adding.delete(key);
    }
</script>

<div class="flex min-h-0 flex-1 flex-col gap-4">
    <form
        class="px-4 md:px-6"
        role="search"
        onsubmit={(event) => {
            event.preventDefault();
            clearTimeout(timer);
            void search();
        }}
    >
        <Input
            type="search"
            icon={MaterialSymbolsSearchRounded}
            placeholder="Songs, artists or a link"
            aria-label="Search music"
            bind:value={text}
            oninput={schedule}
        />
    </form>

    <ScrollRow role="radiogroup" aria-label="Search on" class="shrink-0 px-4 md:px-6">
        {#each SOURCES as option (option.value)}
            <button
                type="button"
                role="radio"
                aria-checked={source === option.value}
                class={[
                    "ripple flex h-8 items-center gap-2 rounded-full px-3 text-xs font-medium whitespace-nowrap transition-colors",
                    source === option.value ? "bg-accent/10 text-accent" : "bg-surface-2 text-mist-400 hover:bg-surface-3 hover:text-mist-100",
                ]}
                {@attach ripple}
                onclick={() => pick(option.value)}
            >
                <BrandIcon brand={option.value} class="size-4" />{option.label}
            </button>
        {/each}
    </ScrollRow>

    <div class="relative min-h-0 flex-1">
        <div bind:this={list} aria-live="polite" class="flex size-full flex-col gap-2 overflow-y-auto overscroll-contain px-2 pb-6 md:px-4">
            {#if searching && !results}
                <ul aria-label="Searching" aria-busy="true" class="flex flex-col gap-1">
                    {#each [64, 48, 72, 56, 40, 68, 52, 60] as width, i (i)}
                        <li class="flex items-center gap-4 p-2">
                            <span class="size-12 shrink-0 animate-pulse rounded-xl bg-surface-2" style:animation-delay="{i * 80}ms"></span>
                            <span class="flex flex-1 flex-col gap-2">
                                <span class="h-4 animate-pulse rounded-full bg-surface-2" style:width="{width}%" style:animation-delay="{i * 80}ms"
                                ></span>
                                <span class="h-3 w-1/4 animate-pulse rounded-full bg-surface-2" style:animation-delay="{i * 80}ms"></span>
                            </span>
                            <span class="h-3 w-8 animate-pulse rounded-full bg-surface-2" style:animation-delay="{i * 80}ms"></span>
                        </li>
                    {/each}
                </ul>
            {:else if problem}
                <p class="px-2 text-sm text-red-400">{problem}</p>
            {:else if results}
                {#if results.playlist}
                    <div class="flex items-center gap-4 rounded-2xl bg-surface-2 p-4">
                        <MaterialSymbolsPlaylistAddRounded class="size-6 shrink-0 text-accent" />
                        <div class="flex min-w-0 flex-1 flex-col">
                            <span class="truncate text-sm font-semibold">{results.playlist.name}</span>
                            <span class="text-xs text-mist-400">
                                Playlist · {formatCount(results.playlist.trackCount)} tracks{results.tracks.length < results.playlist.trackCount
                                    ? `, first ${results.tracks.length} below`
                                    : ""}
                            </span>
                        </div>
                        <button
                            type="button"
                            disabled={adding.has("playlist")}
                            class="ripple flex h-10 items-center gap-2 rounded-full bg-accent px-4 text-sm font-semibold text-cyan-950 hover:bg-cyan-300"
                            {@attach ripple}
                            onclick={() => add("playlist", text.trim())}
                        >
                            {#if adding.has("playlist")}<SvgSpinners90RingWithBg class="size-4" />{/if}Add all
                        </button>
                    </div>
                {/if}
                <ul class={["flex flex-col gap-1 transition-opacity", searching && "opacity-50"]}>
                    {#each results.tracks as track, i (`${i}-${track.identifier}`)}
                        {@const busy = adding.has(track.identifier)}
                        <li>
                            <button
                                type="button"
                                aria-label="Add {track.title} by {track.author} to the queue"
                                aria-busy={busy}
                                disabled={!track.uri}
                                class="ripple flex w-full items-center gap-4 rounded-2xl p-2 text-left transition-colors hover:bg-surface-2 active:bg-surface-3 disabled:opacity-50"
                                {@attach ripple}
                                onclick={() => add(track.identifier, track.uri!)}
                            >
                                <TrackRow {track}>
                                    {#snippet trailing()}
                                        <span class="flex w-12 shrink-0 justify-end pr-2 font-mono text-xs text-mist-400">
                                            {#if busy}<SvgSpinners90RingWithBg class="size-4 text-accent" />{:else}{track.isStream
                                                    ? "Live"
                                                    : time(track.lengthMs)}{/if}
                                        </span>
                                    {/snippet}
                                </TrackRow>
                            </button>
                        </li>
                    {:else}
                        <li class="px-2 text-sm text-mist-400">No results. Try other words, or another source.</li>
                    {/each}
                </ul>
            {:else}
                <p class="px-2 text-sm text-mist-400">Search for a song, or paste a YouTube, Spotify or Apple Music link.</p>
            {/if}
        </div>
        <OverlayScrollbar viewport={list} inset={16} />
    </div>
</div>
