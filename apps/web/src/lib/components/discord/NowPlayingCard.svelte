<script module lang="ts">
    export type NowPlaying = {
        title: string;
        author: string;
        source: string;
        artwork: string | null;
        requester: string | null;
        requesterAvatar: string | null;
        progress: number;
        elapsed: string;
        duration: string;
        stream: boolean;
        paused: boolean;
        volume: number;
        loop: "Disabled" | "Track" | "Queue";
        shuffle: boolean;
        autoplay: boolean;
        filters: string[];
        upNext: string | null;
        upNextArtwork: string | null;
        queued: number;
    };

    const LABELS: Record<string, string> = {
        youtube: "YouTube",
        spotify: "Spotify",
        soundcloud: "SoundCloud",
        http: "Link",
        local: "Local file",
        twitch: "Twitch",
    };
    const FILTERS_SHOWN = 2;
</script>

<script lang="ts">
    import BrandIcon, { brandOf } from "#lib/components/BrandIcon.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import WavyProgress from "#lib/components/ui/WavyProgress.svelte";
    import MaterialSymbolsAutoplayRounded from "~icons/material-symbols/autoplay-rounded";
    import MaterialSymbolsEqualizerRounded from "~icons/material-symbols/equalizer-rounded";
    import MaterialSymbolsMusicNoteRounded from "~icons/material-symbols/music-note-rounded";
    import MaterialSymbolsPauseRounded from "~icons/material-symbols/pause-rounded";
    import MaterialSymbolsPlayArrowRounded from "~icons/material-symbols/play-arrow-rounded";
    import MaterialSymbolsRepeatOneRounded from "~icons/material-symbols/repeat-one-rounded";
    import MaterialSymbolsRepeatRounded from "~icons/material-symbols/repeat-rounded";
    import MaterialSymbolsSensorsRounded from "~icons/material-symbols/sensors-rounded";
    import MaterialSymbolsShuffleRounded from "~icons/material-symbols/shuffle-rounded";
    import MaterialSymbolsVolumeUpRounded from "~icons/material-symbols/volume-up-rounded";

    let { data }: { data: NowPlaying } = $props();

    const logo = $derived(brandOf(data.source));
    const looping = $derived(data.loop !== "Disabled");
    const filters = $derived.by(() => {
        const shown = data.filters.slice(0, FILTERS_SHOWN).join(" · ");
        const hidden = data.filters.length - FILTERS_SHOWN;
        return hidden > 0 ? `${shown} +${hidden}` : shown;
    });
</script>

{#snippet artwork(src: string | null, className: string)}
    {#if src}
        <img {src} alt="" class={["shrink-0 object-cover", className]} />
    {:else}
        <span class={["flex shrink-0 items-center justify-center bg-surface-2 text-accent", className]}
            ><MaterialSymbolsMusicNoteRounded class="size-2/5" /></span
        >
    {/if}
{/snippet}

<div class="flex w-180 flex-col gap-6 bg-surface-1 p-6 font-sans text-mist-100">
    <div class="flex gap-6">
        {@render artwork(data.artwork, "size-40 rounded-2xl")}
        <div class="flex min-w-0 flex-1 flex-col">
            <div class="flex gap-2">
                {#if data.stream}
                    <Chip tone="danger"><MaterialSymbolsSensorsRounded />Live</Chip>
                {:else if data.paused}
                    <Chip tone="warning"><MaterialSymbolsPlayArrowRounded />Paused</Chip>
                {:else}
                    <Chip tone="accent"><MaterialSymbolsPauseRounded />Playing</Chip>
                {/if}
                <Chip>
                    {#if logo}<BrandIcon brand={logo} class="size-4" />{:else}<MaterialSymbolsMusicNoteRounded />{/if}
                    {LABELS[data.source] ?? (data.source ? data.source[0].toUpperCase() + data.source.slice(1) : "Music")}
                </Chip>
            </div>
            <span class="mt-4 truncate font-display text-2xl font-semibold tracking-tight">{data.title}</span>
            <span class="mt-0.5 truncate text-mist-400">{data.author}</span>
            {#if data.requester}
                <div class="mt-auto flex items-center gap-2 text-sm text-mist-400">
                    <Avatar src={data.requesterAvatar} name={data.requester} class="size-6 text-xs" />
                    <span class="truncate">Requested by {data.requester}</span>
                </div>
            {/if}
        </div>
    </div>

    <div class="flex flex-col gap-2">
        <WavyProgress value={data.stream ? 1 : data.progress} playing={!data.paused} />
        <div class="flex justify-between font-mono text-xs text-mist-400">
            <span>{data.elapsed}</span>
            <span>{data.stream ? "Live" : data.duration}</span>
        </div>
    </div>

    <div class="flex flex-col gap-4">
        <div class="flex gap-2">
            <Chip class="font-mono"><MaterialSymbolsVolumeUpRounded />{data.volume}%</Chip>
            <Chip tone={data.shuffle ? "on" : "muted"}><MaterialSymbolsShuffleRounded />Shuffle</Chip>
            <Chip tone={looping ? "on" : "muted"}>
                {#if data.loop === "Track"}<MaterialSymbolsRepeatOneRounded />{:else}<MaterialSymbolsRepeatRounded />{/if}{looping
                    ? `Loop ${data.loop.toLowerCase()}`
                    : "Loop off"}
            </Chip>
            <Chip tone={data.autoplay ? "on" : "muted"}><MaterialSymbolsAutoplayRounded />Autoplay</Chip>
            {#if filters}<Chip tone="violet"><MaterialSymbolsEqualizerRounded />{filters}</Chip>{/if}
        </div>
        <div class={["flex h-12 items-center gap-2 rounded-2xl bg-surface-2 pr-4", data.upNext ? "pl-2" : "pl-4"]}>
            {#if data.upNext}{@render artwork(data.upNextArtwork, "size-8 rounded-lg")}{/if}
            <div class="flex min-w-0 flex-col">
                <span class="font-mono text-[10px] leading-3 font-semibold tracking-wider text-mist-400 uppercase">
                    {data.queued ? `Up next · ${data.queued} queued` : "Up next"}
                </span>
                {#if data.upNext}
                    <span class="truncate text-sm font-medium">{data.upNext}</span>
                {:else}
                    <span class="text-sm font-medium text-mist-400">Nothing queued</span>
                {/if}
            </div>
        </div>
    </div>
</div>
