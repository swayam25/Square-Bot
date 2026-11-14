<script lang="ts">
    import Island from "#lib/components/Island.svelte";
    import Drawer from "#lib/components/ui/Drawer.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import OverlayScrollbar from "#lib/components/ui/OverlayScrollbar.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { formatCount } from "#lib/format.ts";
    import { trackLyrics } from "#lib/lyrics.remote.ts";
    import { mobile } from "#lib/media.ts";
    import { ripple } from "#lib/motion.ts";
    import * as music from "#lib/music.remote.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import MaterialSymbolsHistoryRounded from "~icons/material-symbols/history-rounded";
    import MaterialSymbolsLyricsRounded from "~icons/material-symbols/lyrics-rounded";
    import MaterialSymbolsQueueMusicRounded from "~icons/material-symbols/queue-music-rounded";
    import MaterialSymbolsSearchRounded from "~icons/material-symbols/search-rounded";
    import type { PageProps } from "./$types";
    import ArtPanel from "./ArtPanel.svelte";
    import ControlsBar from "./ControlsBar.svelte";
    import { control, locked, type Access, type Tab } from "./player.ts";
    import SidePanel from "./SidePanel.svelte";
    import SkipVote from "./SkipVote.svelte";
    import ZenView, { enterFullscreen } from "./ZenView.svelte";

    let { data }: PageProps = $props();

    const guild = $derived(data.guild.id);
    const playerQuery = $derived(music.livePlayer(guild));
    const queueQuery = $derived(music.liveQueue(guild));
    const statusQuery = music.liveStatus();

    const player = $derived(playerQuery.current);
    const access = $derived<Access>({
        dj: player?.viewer.dj ?? false,
        inChannel: player?.viewer.inChannel ?? false,
        queueLock: player?.viewer.queueLock ?? null,
        me: data.user?.id ?? null,
    });
    const queue = $derived(queueQuery.current);
    const online = $derived(statusQuery.connected && (statusQuery.current ?? false));

    let now = $state(Date.now());
    $effect(() => {
        if (!player?.track || player.paused || !online) return;
        let frame = requestAnimationFrame(function tick() {
            now = Date.now();
            frame = requestAnimationFrame(tick);
        });
        return () => cancelAnimationFrame(frame);
    });

    const playhead = $derived.by(() => {
        if (!player?.track) return 0;
        const elapsed = player.paused || !online ? 0 : Math.max(0, now - player.positionAt);
        const at = player.positionMs + elapsed;
        return player.track.isStream ? at : Math.min(at, player.track.lengthMs);
    });

    // The released spot is held until the bot's next push, so nothing flicks back to the old one meanwhile
    let seeking = $state<number | null>(null);
    let held = $state<{ ms: number; since: number } | null>(null);
    const heldMs = $derived(held && player?.positionAt === held.since ? held.ms : null);
    const position = $derived(player?.track && seeking !== null ? seeking * player.track.lengthMs : (heldMs ?? playhead));

    async function seek(ms: number) {
        if (!player) return;
        const since = player.positionAt;
        const target = { ms, since };
        held = target;
        const ok = await control(music.seekTrack({ guild, positionMs: ms }));
        setTimeout(() => held === target && (held = null), ok ? 1500 : 0);
    }

    let heard: { guild: string; at: number | null } | null = null;
    $effect(() => {
        if (!player) return;
        const failure = player.failure;
        const at = failure?.at ?? null;
        if (failure && heard?.guild === guild && heard.at !== at) {
            toast.error(`Couldn't play ${failure.title}`, {
                description: failure.reason ?? "The music server couldn't load it. Try another song or source.",
            });
        }
        heard = { guild, at };
    });

    const track = $derived(player?.track ?? null);
    const lyricsQuery = $derived(
        track && !track.isStream ? trackLyrics({ title: track.title, artist: track.author, durationMs: track.lengthMs }) : null,
    );
    const lyricsOff = $derived.by(() => {
        if (!track) return "Lyrics show up while a song plays";
        if (track.isStream) return "Live streams don't have lyrics";
        const found = lyricsQuery?.current;
        if (found === null) return "No lyrics for this song";
        if (found?.instrumental) return "Instrumental, nothing to sing along to";
        return false;
    });

    // Picked once per server, then only by the user. Plain state because a writable $derived re-ran on track changes
    let picked = $state<{ guild: string; tab: Tab } | null>(null);
    $effect(() => {
        if (picked?.guild === guild || !player || !queue) return;
        picked = { guild, tab: !player.track ? "search" : queue.total ? "queue" : "lyrics" };
    });
    const tab = $derived(picked?.guild === guild ? picked.tab : "search");
    const setTab = (next: Tab) => (picked = { guild, tab: next });
    let sheet = $state(false);
    const TAB_TITLES: Record<Tab, string> = { search: "Search", queue: "Queue", history: "History", lyrics: "Lyrics" };
    function openSheet(next: Tab) {
        setTab(next);
        sheet = true;
    }

    const hasTrack = $derived(!!track);
    let zen = $derived.by(() => (void hasTrack, false));
    function openZen() {
        enterFullscreen();
        zen = true;
    }

    let scroller = $state<HTMLElement | null>(null);
    const server = $derived({
        name: data.guild.name,
        iconUrl: data.guild.iconUrl,
        href: data.guild.canManage ? `/guild/${guild}/music` : `/guild/${guild}`,
    });
</script>

<svelte:head>
    <title>Player · {data.guild.name} · Square</title>
</svelte:head>

{#snippet sheetButton(value: Tab, label: string, Icon: typeof MaterialSymbolsSearchRounded, off: string | false = false, count?: number)}
    <Tooltip content={off || label}>
        <!-- The badge sits beside the button, which clips anything outside it for the ripple -->
        <span class="relative flex">
            <button
                type="button"
                aria-haspopup="dialog"
                disabled={!!off}
                class="ripple flex size-12 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-100 disabled:opacity-40"
                {@attach ripple}
                onclick={() => openSheet(value)}
            >
                <Icon class="size-6" />
            </button>
            {#if count}
                <span
                    aria-hidden="true"
                    class="pointer-events-none absolute top-1 right-0 rounded-full bg-accent px-1.5 font-mono text-2xs leading-4 font-semibold text-cyan-950"
                >
                    {formatCount(count)}
                </span>
            {/if}
        </span>
    </Tooltip>
{/snippet}

{#snippet dock()}
    {@render sheetButton("search", "Search", MaterialSymbolsSearchRounded)}
    {@render sheetButton("queue", "Queue", MaterialSymbolsQueueMusicRounded, false, queue?.total)}
    {@render sheetButton("history", "History", MaterialSymbolsHistoryRounded)}
    {@render sheetButton("lyrics", "Lyrics", MaterialSymbolsLyricsRounded, lyricsOff)}
{/snippet}

<div class="flex h-dvh overflow-hidden bg-gray-900 md:p-2">
    <div class="relative min-h-0 min-w-0 flex-1 animate-shell-in overflow-hidden bg-gray-950 md:rounded-4xl">
        <main
            bind:this={scroller}
            class="flex size-full flex-col gap-2 overflow-y-auto overscroll-contain p-2 max-md:overflow-hidden max-md:pb-[max(0.5rem,env(safe-area-inset-bottom))] lg:overflow-hidden"
        >
            {#if player}
                {#if mobile.current}
                    <ArtPanel {player} position={playhead} {server} {online} onzen={openZen} />
                    {#if player.vote}<SkipVote {guild} {player} vote={player.vote} {access} />{/if}
                    <ControlsBar {guild} {player} {position} {access} queued={queue?.total ?? 0} bind:seeking onseek={seek} {dock} />
                    <Drawer bind:open={sheet} title={TAB_TITLES[tab]} plain class="h-[calc(100dvh-4rem)]">
                        <SidePanel {guild} {player} {queue} {position} {online} {lyricsOff} {access} bind:tab={() => tab, setTab} sheet />
                    </Drawer>
                {:else}
                    <div class="grid gap-2 lg:min-h-0 lg:flex-1 lg:grid-cols-2">
                        <ArtPanel {player} position={playhead} {server} {online} onzen={openZen} />
                        <SidePanel {guild} {player} {queue} {position} {online} {lyricsOff} {access} bind:tab={() => tab, setTab} />
                    </div>
                    {#if player.vote}<SkipVote {guild} {player} vote={player.vote} {access} />{/if}
                    <ControlsBar {guild} {player} {position} {access} queued={queue?.total ?? 0} bind:seeking onseek={seek} />
                {/if}
            {:else if playerQuery.error}
                <EmptyState
                    tone="danger"
                    card
                    class="flex-1"
                    title="Couldn't load the player"
                    text={playerQuery.error.message ?? "Square didn't answer. Try again in a moment."}
                    retry={() => playerQuery.reconnect()}
                />
            {:else}
                <div aria-hidden="true" class="grid flex-1 gap-2 md:flex-none lg:min-h-0 lg:flex-1 lg:grid-cols-2">
                    <div class="h-full skeleton rounded-3xl md:h-112 lg:h-auto"></div>
                    <div class="hidden h-112 skeleton rounded-3xl md:block lg:h-auto"></div>
                </div>
                <div aria-hidden="true" class="h-24 shrink-0 skeleton rounded-3xl"></div>
            {/if}
        </main>
        <OverlayScrollbar viewport={scroller} inset={24} />
        <!-- Full-bleed on phones, so there is no frame edge for the island to bulge out of -->
        <Island docked={!mobile.current} />
    </div>
</div>

{#if player?.track}
    <ZenView bind:open={zen} {guild} track={player.track} {position} playing={!player.paused && online} {lyricsOff} lock={locked(access)} />
{/if}
