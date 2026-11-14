<script lang="ts">
    import DiscordDownload from "#lib/components/discord/DiscordDownload.svelte";
    import DiscordTooltip from "#lib/components/discord/DiscordTooltip.svelte";
    import { time } from "#lib/format.ts";
    import type { ClassValue } from "svelte/elements";
    import MaterialSymbolsFullscreenExitRounded from "~icons/material-symbols/fullscreen-exit-rounded";
    import MaterialSymbolsFullscreenRounded from "~icons/material-symbols/fullscreen-rounded";
    import MaterialSymbolsPauseRounded from "~icons/material-symbols/pause-rounded";
    import MaterialSymbolsPlayArrowRounded from "~icons/material-symbols/play-arrow-rounded";
    import MaterialSymbolsVolumeOffRounded from "~icons/material-symbols/volume-off-rounded";
    import MaterialSymbolsVolumeUpRounded from "~icons/material-symbols/volume-up-rounded";

    let {
        src,
        name,
        width,
        height,
        class: className,
    }: { src: string; name?: string; width?: number | null; height?: number | null; class?: ClassValue } = $props();

    let box = $state<HTMLElement | null>(null);
    let video = $state<HTMLVideoElement | null>(null);
    let paused = $state(true);
    let current = $state(0);
    let duration = $state(0);
    let buffered = $state<{ start: number; end: number }[]>([]);
    let muted = $state(false);
    let volume = $state(1);
    let full = $state(false);
    let started = $state(false);
    let awake = $state(false);
    let dragging = $state<"seek" | "volume" | null>(null);
    let hover = $state<{ x: number; at: number } | null>(null);
    let flash = $state<{ key: number; playing: boolean } | null>(null);
    let sleep: ReturnType<typeof setTimeout> | undefined;

    const bar = $derived(started && (paused || awake || dragging !== null));
    const percent = (seconds: number) => (duration ? Math.min(100, (seconds / duration) * 100) : 0);
    const loaded = $derived(buffered.find((range) => range.start <= current && current <= range.end + 0.5)?.end ?? current);
    const loudness = $derived(muted ? 0 : volume);

    function wake() {
        awake = true;
        clearTimeout(sleep);
        sleep = setTimeout(() => (awake = false), 2500);
    }

    function toggle() {
        if (!video) return;
        started = true;
        if (video.paused) void video.play();
        else video.pause();
    }

    function click() {
        toggle();
        flash = { key: (flash?.key ?? 0) + 1, playing: !video?.paused };
    }

    const clamp = (value: number) => Math.min(1, Math.max(0, value));

    function drag(kind: "seek" | "volume", event: PointerEvent) {
        const track = (event.currentTarget as HTMLElement).getBoundingClientRect();
        if (!track.width || !track.height) return;
        if (kind === "seek") {
            if (video && duration) video.currentTime = clamp((event.clientX - track.left) / track.width) * duration;
        } else {
            volume = clamp((track.bottom - event.clientY) / track.height);
            muted = volume === 0;
        }
    }

    function press(kind: "seek" | "volume", event: PointerEvent) {
        (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
        dragging = kind;
        drag(kind, event);
    }

    function aim(event: PointerEvent) {
        const track = (event.currentTarget as HTMLElement).getBoundingClientRect();
        if (!track.width || !duration) return;
        const ratio = clamp((event.clientX - track.left) / track.width);
        hover = { x: ratio * 100, at: ratio * duration };
        if (dragging === "seek") drag("seek", event);
    }

    function fullscreen() {
        if (document.fullscreenElement) void document.exitFullscreen();
        else void box?.requestFullscreen();
    }

    $effect(() => {
        const sync = () => (full = document.fullscreenElement === box);
        document.addEventListener("fullscreenchange", sync);
        return () => {
            document.removeEventListener("fullscreenchange", sync);
            clearTimeout(sleep);
        };
    });

    const control = "flex shrink-0 cursor-pointer items-center justify-center text-white";
</script>

<div
    bind:this={box}
    role="group"
    aria-label="Video"
    class={["relative overflow-hidden bg-black", full ? "flex items-center" : "rounded-lg", className]}
    onpointermove={wake}
    onpointerleave={() => (awake = false)}
>
    <!-- svelte-ignore a11y_media_has_caption -->
    <video
        bind:this={video}
        bind:paused
        bind:currentTime={current}
        bind:duration
        bind:buffered
        bind:muted
        bind:volume
        {src}
        {width}
        {height}
        preload="metadata"
        playsinline
        class={["block cursor-pointer", full ? "size-full object-contain" : "max-h-full w-full"]}
        onclick={click}
        onplay={() => (started = true)}
    ></video>

    {#if !started}
        <DiscordTooltip content="Play" class="absolute top-1/2 left-1/2 -translate-1/2">
            <button
                type="button"
                class="flex size-12 cursor-pointer items-center justify-center rounded-full bg-black/60 text-dc-media-icon hover:text-white"
                onclick={toggle}
            >
                <MaterialSymbolsPlayArrowRounded class="size-7" />
            </button>
        </DiscordTooltip>
    {/if}

    {#key flash?.key}
        {#if flash}
            <span
                aria-hidden="true"
                class="pointer-events-none absolute top-1/2 left-1/2 -mt-10 -ml-10 flex size-20 animate-dc-video-flash items-center justify-center rounded-full bg-black/60 text-dc-media-icon"
            >
                {#if flash.playing}<MaterialSymbolsPlayArrowRounded class="size-12" />{:else}<MaterialSymbolsPauseRounded class="size-12" />{/if}
            </span>
        {/if}
    {/key}

    <DiscordDownload {src} {name} class={awake ? "opacity-100" : "pointer-events-none opacity-0"} />

    <div
        class={[
            "absolute inset-x-0 bottom-0 flex h-8 items-center gap-2.5 bg-black/80 px-0.5 transition-opacity duration-200",
            bar ? "opacity-100" : "pointer-events-none opacity-0",
        ]}
    >
        <DiscordTooltip content={paused ? "Play" : "Pause"} placement="bottom">
            <button type="button" class={[control, "mr-2 size-6 [&_svg]:size-6"]} onclick={toggle}>
                {#if paused}<MaterialSymbolsPlayArrowRounded />{:else}<MaterialSymbolsPauseRounded />{/if}
            </button>
        </DiscordTooltip>
        <span class="shrink-0 font-mono text-[13px] leading-none text-white tabular-nums">{time(current * 1000)}/{time(duration * 1000)}</span>
        <div
            role="slider"
            tabindex="0"
            aria-label="Seek"
            aria-valuemin={0}
            aria-valuemax={Math.round(duration)}
            aria-valuenow={Math.round(current)}
            class="group/track relative flex h-full flex-1 cursor-pointer items-center"
            onpointerdown={(event) => press("seek", event)}
            onpointermove={aim}
            onpointerleave={() => (hover = null)}
            onpointerup={() => (dragging = null)}
            onpointercancel={() => (dragging = null)}
            onkeydown={(event) => {
                if (!video) return;
                if (event.key === "ArrowRight") video.currentTime = Math.min(duration, current + 5);
                else if (event.key === "ArrowLeft") video.currentTime = Math.max(0, current - 5);
            }}
        >
            <div class="relative h-1.5 w-full rounded-full bg-white/22">
                <div class="absolute inset-y-0 left-0 rounded-full bg-white/45" style:width="{percent(loaded)}%"></div>
                <div class="absolute inset-y-0 left-0 rounded-full bg-dc-blurple" style:width="{percent(current)}%"></div>
                <div
                    class={[
                        "absolute top-1/2 size-2.5 -translate-1/2 rounded-full bg-dc-blurple transition-opacity",
                        dragging === "seek" ? "opacity-100" : "opacity-0 group-hover/track:opacity-100",
                    ]}
                    style:left="{percent(current)}%"
                ></div>
            </div>
            {#if hover}
                <span
                    class="pointer-events-none absolute bottom-full mb-px h-4 -translate-x-1/2 rounded-sm bg-black px-1.5 text-xs leading-4 font-semibold text-white tabular-nums"
                    style:left="{hover.x}%"
                >
                    {time(hover.at * 1000)}
                </span>
            {/if}
        </div>
        <div class="group/volume relative flex">
            <div
                class={[
                    "absolute bottom-full left-1/2 -translate-x-1/2 pb-2.75 transition-opacity duration-200",
                    dragging === "volume"
                        ? "opacity-100"
                        : "pointer-events-none opacity-0 group-hover/volume:pointer-events-auto group-hover/volume:opacity-100",
                ]}
            >
                <div
                    role="slider"
                    tabindex="0"
                    aria-label="Volume"
                    aria-orientation="vertical"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={Math.round(loudness * 100)}
                    class="group/slider flex h-21 w-3 cursor-pointer justify-center rounded-full bg-black/80 p-0.75"
                    onpointerdown={(event) => press("volume", event)}
                    onpointermove={(event) => dragging === "volume" && drag("volume", event)}
                    onpointerup={() => (dragging = null)}
                    onpointercancel={() => (dragging = null)}
                    onkeydown={(event) => {
                        const step = event.key === "ArrowUp" ? 0.1 : event.key === "ArrowDown" ? -0.1 : 0;
                        if (!step) return;
                        volume = clamp(loudness + step);
                        muted = volume === 0;
                    }}
                >
                    <div class="relative w-1.5 rounded-full bg-white/30">
                        <div class="absolute inset-x-0 bottom-0 rounded-full bg-dc-blurple" style:height="{loudness * 100}%"></div>
                        <div
                            class={[
                                "absolute left-1/2 size-2.5 -translate-x-1/2 translate-y-1/2 rounded-full bg-dc-blurple transition-opacity",
                                dragging === "volume" ? "opacity-100" : "opacity-0 group-hover/slider:opacity-100",
                            ]}
                            style:bottom="{loudness * 100}%"
                        ></div>
                    </div>
                </div>
            </div>
            <DiscordTooltip content={muted ? "Unmute" : "Mute"} placement="bottom">
                <button type="button" class={[control, "size-6 [&_svg]:size-6"]} onclick={() => (muted = !muted)}>
                    {#if loudness === 0}<MaterialSymbolsVolumeOffRounded />{:else}<MaterialSymbolsVolumeUpRounded />{/if}
                </button>
            </DiscordTooltip>
        </div>
        <DiscordTooltip content={full ? "Exit Full Screen" : "Full Screen"} placement="bottom">
            <button type="button" class={[control, "size-7 [&_svg]:size-7"]} onclick={fullscreen}>
                {#if full}<MaterialSymbolsFullscreenExitRounded />{:else}<MaterialSymbolsFullscreenRounded />{/if}
            </button>
        </DiscordTooltip>
    </div>
</div>
