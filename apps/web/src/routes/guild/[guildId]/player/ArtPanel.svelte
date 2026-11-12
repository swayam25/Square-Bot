<script lang="ts">
    import BrandIcon, { brandOf, type Brand } from "#lib/components/BrandIcon.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import Cover from "#lib/components/ui/Cover.svelte";
    import GuildIcon from "#lib/components/ui/GuildIcon.svelte";
    import ScrollRow from "#lib/components/ui/ScrollRow.svelte";
    import Segmented from "#lib/components/ui/Segmented.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { ripple } from "#lib/motion.ts";
    import type { PlayerState } from "@square/api-client";
    import { untrack } from "svelte";
    import MaterialSymbolsArrowBackRounded from "~icons/material-symbols/arrow-back-rounded";
    import MaterialSymbolsFullscreenRounded from "~icons/material-symbols/fullscreen-rounded";
    import MaterialSymbolsMusicNoteRounded from "~icons/material-symbols/music-note-rounded";
    import MaterialSymbolsSmartDisplayRounded from "~icons/material-symbols/smart-display-rounded";
    import Listeners from "./Listeners.svelte";

    let {
        player,
        position,
        server,
        online,
        onzen,
    }: {
        player: PlayerState;
        position: number;
        server: { name: string; iconUrl: string | null; href: string };
        online: boolean;
        onzen: () => void;
    } = $props();

    const track = $derived(player.track);
    let mode = $state<"music" | "video">("music");

    const LABELS: Record<Brand, string> = {
        youtube_music: "YT Music",
        youtube: "YouTube",
        spotify: "Spotify",
        apple_music: "Apple Music",
        soundcloud: "SoundCloud",
    };
    const brand = $derived(track ? brandOf(track.source) : undefined);
    const source = $derived(brand ? { brand, label: LABELS[brand] } : undefined);

    // Only YouTube tracks have a video: their identifier is the video's ID
    const videoId = $derived(track?.source === "youtube" && /^[\w-]{11}$/.test(track.identifier) ? track.identifier : null);
    let frame = $state<HTMLIFrameElement | null>(null);
    // Captured once per video: later moves go through the player API instead of reloading the frame
    const start = $derived.by(() => (videoId ? untrack(() => Math.floor(position / 1000)) : 0));
    const embed = $derived.by(() => {
        if (!videoId) return null;
        const params = new URLSearchParams({
            enablejsapi: "1",
            origin: location.origin,
            autoplay: "1",
            mute: "1",
            controls: "0",
            disablekb: "1",
            fs: "0",
            iv_load_policy: "3",
            rel: "0",
            playsinline: "1",
            start: String(start),
        });
        return `https://www.youtube-nocookie.com/embed/${videoId}?${params}`;
    });

    // Video stays picked across songs, but a song without one shows its art
    const view = $derived(mode === "video" && embed ? "video" : "music");

    const DRIFT_S = 0.5;
    const SETTLE_MS = 1500;
    // What the embed last told us: its time, when it said so, and its state (1 playing, 2 paused, 3 buffering, 0 ended)
    let video = { time: 0, at: 0, state: -1 };
    let corrected = 0;
    let shown = $state(false);

    function send(func: string, args: unknown[] = []) {
        frame?.contentWindow?.postMessage(JSON.stringify({ event: "command", func, args }), "*");
    }

    // Seeks only when the video has drifted, so it never stutters on every bot push
    function sync(force = false) {
        if (!frame) return;
        const now = performance.now();
        const want = position / 1000;
        const have = video.time + (video.state === 1 ? (now - video.at) / 1000 : 0);
        if (force || (video.at && Math.abs(want - have) > DRIFT_S && now - corrected > SETTLE_MS)) {
            send("seekTo", [want, true]);
            corrected = now;
        }
        if (player.paused && video.state !== 2) send("pauseVideo");
        else if (!player.paused && video.state !== 1 && video.state !== 3) send("playVideo");
    }

    $effect(() => {
        if (!embed) return;
        video = { time: 0, at: 0, state: -1 };
        shown = false;
        const onMessage = (event: MessageEvent) => {
            if (event.source !== frame?.contentWindow || typeof event.data !== "string") return;
            let data: { event?: string; info?: { currentTime?: number; playerState?: number } };
            try {
                data = JSON.parse(event.data);
            } catch {
                return;
            }
            if (data.event !== "infoDelivery" || !data.info) return;
            if (typeof data.info.currentTime === "number") video = { ...video, time: data.info.currentTime, at: performance.now() };
            if (typeof data.info.playerState === "number") video = { ...video, state: data.info.playerState };
            // Kept hidden until it really plays, so YouTube's loading screen and end cards never show
            shown = video.state === 1 || video.state === 2;
        };
        addEventListener("message", onMessage);
        const timer = setInterval(() => untrack(() => sync()), 1000);
        return () => {
            removeEventListener("message", onMessage);
            clearInterval(timer);
        };
    });

    // Pauses, resumes and seeks show up as a fresh `positionAt`, so the video follows them right away
    $effect(() => {
        void player.positionAt;
        void player.paused;
        untrack(() => sync(true));
    });

    function listen() {
        frame?.contentWindow?.postMessage(JSON.stringify({ event: "listening", id: 1, channel: "widget" }), "*");
        sync(true);
    }
</script>

<section
    aria-label="Now playing"
    class="relative isolate flex min-h-0 flex-1 flex-col items-center overflow-clip rounded-3xl bg-surface-1 p-4 md:min-h-112 md:p-6 lg:min-h-0"
>
    {#if track?.artworkUrl}
        <img
            src={track.artworkUrl}
            alt=""
            aria-hidden="true"
            referrerpolicy="no-referrer"
            class="absolute inset-0 -z-10 size-full scale-125 object-cover opacity-40 blur-3xl"
        />
        <span aria-hidden="true" class="absolute inset-0 -z-10 bg-linear-to-b from-mist-950/20 to-mist-950/70"></span>
    {/if}

    <div class="flex w-full items-center justify-between gap-4">
        <a
            href={server.href}
            aria-label="Back to the {server.name} dashboard"
            class="group flex min-w-0 items-center gap-2 rounded-full bg-black/30 py-1 pr-4 pl-1 backdrop-blur-xl transition-colors hover:bg-black/50"
        >
            <span class="relative size-8 shrink-0">
                <GuildIcon src={server.iconUrl} name={server.name} class="size-8 rounded-full transition-opacity group-hover:opacity-0" />
                <MaterialSymbolsArrowBackRounded class="absolute inset-0 m-auto size-5 opacity-0 transition-opacity group-hover:opacity-100" />
            </span>
            <span class="truncate text-sm font-semibold">{server.name}</span>
            <span
                title={online ? "Live" : "Offline, showing the last known state"}
                class={["size-2 shrink-0 rounded-full", online ? "bg-emerald-400" : "animate-pulse bg-amber-400"]}
            ></span>
        </a>
        <Segmented
            label="Show"
            options={[
                { value: "music", label: "Music", icon: MaterialSymbolsMusicNoteRounded },
                {
                    value: "video",
                    label: "Video",
                    icon: MaterialSymbolsSmartDisplayRounded,
                    disabled: embed ? false : track ? "Only YouTube tracks have a video" : "Nothing is playing",
                },
            ]}
            bind:value={() => view, (next) => (mode = next)}
            class="shrink-0 bg-black/30 backdrop-blur-xl"
            pill="bg-white/15"
        />
    </div>

    <div class="flex min-h-0 w-full flex-1 flex-col items-center justify-center gap-4 py-4 md:gap-6 md:py-6">
        <!-- Sized by the room it gets, so the art shrinks to fit a short phone instead of pushing the controls off -->
        <div class="[container-type:size] grid min-h-0 w-full flex-1 place-items-center md:max-lg:min-h-80">
            {#if view === "video"}
                <!-- Taller than its box, so YouTube's title bar and bottom bar sit in the cropped-off letterbox -->
                <div class="relative aspect-video w-[min(100cqw,calc(100cqh*16/9))] overflow-hidden rounded-3xl bg-black shadow-2xl shadow-black/50">
                    {#if track?.artworkUrl}<img
                            src={track.artworkUrl}
                            alt=""
                            referrerpolicy="no-referrer"
                            class="absolute inset-0 size-full object-cover blur-sm"
                        />{/if}
                    {#key videoId}
                        <iframe
                            bind:this={frame}
                            src={embed}
                            title="Video for {track?.title}"
                            tabindex="-1"
                            allow="autoplay; encrypted-media"
                            onload={listen}
                            class={[
                                "pointer-events-none absolute inset-x-0 -top-24 h-[calc(100%+12rem)] w-full transition-opacity duration-500",
                                shown ? "opacity-100" : "opacity-0",
                            ]}
                        ></iframe>
                    {/key}
                </div>
            {:else}
                <Cover src={track?.artworkUrl} class="size-[min(100cqw,100cqh,20rem)] rounded-4xl text-accent shadow-2xl shadow-black/50" />
            {/if}
        </div>

        <div class="flex w-full max-w-md flex-col items-center gap-2 text-center">
            {#if track}
                <h2 class="line-clamp-2 font-display text-2xl font-semibold md:text-3xl">{track.title}</h2>
                <p class="truncate text-mist-400">{track.author}</p>
            {:else}
                <h2 class="font-display text-2xl font-semibold">Nothing is playing</h2>
                <p class="text-sm text-mist-400">Add a song from search to start.</p>
            {/if}
        </div>
    </div>

    {#if track || player.listeners.length}
        <div class="grid w-full grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-end gap-2">
            <div class="flex min-w-0">
                {#if track?.requester}
                    <span class="flex h-10 min-w-0 items-center gap-2 rounded-full bg-black/30 pr-4 pl-1 text-sm backdrop-blur-xl">
                        <Avatar src={track.requester.avatarUrl} name={track.requester.name} class="size-8 text-xs" />
                        <span class="flex min-w-0 flex-col leading-tight">
                            <span class="text-2xs text-mist-400">Requested by</span>
                            <span class="truncate font-semibold">{track.requester.name}</span>
                        </span>
                    </span>
                {/if}
            </div>
            <div class="flex justify-center"><Listeners listeners={player.listeners} /></div>
            <div class="flex min-w-0 items-center justify-end gap-2">
                {#if player.eq.length}
                    <ScrollRow aria-label="Sound effects" class="min-w-0">
                        {#each player.eq as name (name)}<Chip tone="violet">{name}</Chip>{/each}
                    </ScrollRow>
                {/if}
                {#if source}
                    <span
                        class="flex h-10 items-center gap-2 rounded-full bg-black/30 px-4 text-sm font-semibold backdrop-blur-xl max-sm:w-10 max-sm:justify-center max-sm:px-0"
                    >
                        <BrandIcon brand={source.brand} class="size-5" /><span class="max-sm:sr-only">{source.label}</span>
                    </span>
                {/if}
                {#if track}
                    <Tooltip content="Full screen">
                        <button
                            type="button"
                            aria-label="Full screen"
                            aria-haspopup="dialog"
                            class="ripple flex size-10 items-center justify-center rounded-full bg-black/30 backdrop-blur-xl transition-colors hover:bg-black/50"
                            {@attach ripple}
                            onclick={onzen}
                        >
                            <MaterialSymbolsFullscreenRounded class="size-5" />
                        </button>
                    </Tooltip>
                {/if}
            </div>
        </div>
    {/if}
</section>
