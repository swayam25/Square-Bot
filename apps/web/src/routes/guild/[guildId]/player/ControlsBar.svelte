<script lang="ts">
    import Drawer from "#lib/components/ui/Drawer.svelte";
    import Slider from "#lib/components/ui/Slider.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import WavyProgress from "#lib/components/ui/WavyProgress.svelte";
    import { time } from "#lib/format.ts";
    import { mobile } from "#lib/media.ts";
    import { ripple } from "#lib/motion.ts";
    import * as music from "#lib/music.remote.ts";
    import type { PlayerState } from "@square/api-client";
    import type { Snippet } from "svelte";
    import MaterialSymbolsAutoplayRounded from "~icons/material-symbols/autoplay-rounded";
    import MaterialSymbolsMoreHorizRounded from "~icons/material-symbols/more-horiz-rounded";
    import MaterialSymbolsPauseRounded from "~icons/material-symbols/pause-rounded";
    import MaterialSymbolsPlayArrowRounded from "~icons/material-symbols/play-arrow-rounded";
    import MaterialSymbolsRepeatOneRounded from "~icons/material-symbols/repeat-one-rounded";
    import MaterialSymbolsRepeatRounded from "~icons/material-symbols/repeat-rounded";
    import MaterialSymbolsShuffleRounded from "~icons/material-symbols/shuffle-rounded";
    import MaterialSymbolsSkipNextRounded from "~icons/material-symbols/skip-next-rounded";
    import MaterialSymbolsSkipPreviousRounded from "~icons/material-symbols/skip-previous-rounded";
    import MaterialSymbolsStopRounded from "~icons/material-symbols/stop-rounded";
    import MaterialSymbolsVolumeDownRounded from "~icons/material-symbols/volume-down-rounded";
    import MaterialSymbolsVolumeMuteRounded from "~icons/material-symbols/volume-mute-rounded";
    import MaterialSymbolsVolumeOffRounded from "~icons/material-symbols/volume-off-rounded";
    import MaterialSymbolsVolumeUpRounded from "~icons/material-symbols/volume-up-rounded";
    import SvgSpinners90RingWithBg from "~icons/svg-spinners/90-ring-with-bg";
    import Equalizer from "./Equalizer.svelte";
    import { control, locked, skipping, type Access } from "./player.ts";

    let {
        guild,
        player,
        position,
        seeking = $bindable(null),
        onseek,
        access,
        queued,
        dock,
    }: {
        guild: string;
        player: PlayerState;
        access: Access;
        queued: number;
        position: number;
        seeking?: number | null;
        onseek: (ms: number) => void;
        dock?: Snippet;
    } = $props();

    const track = $derived(player.track);
    const playing = $derived(!!track && !player.paused);
    const lock = $derived(locked(access));
    // The bot refuses these with nothing playing, and shuffle and queue looping also need songs waiting
    const idle = $derived(lock ?? (track ? null : "Nothing is playing"));
    const shuffleLock = $derived(idle ?? (queued ? null : "Add songs to the queue first"));
    const skip = $derived(skipping(player, access));
    const skipLabel = $derived(skip.now ? "Next" : player.vote ? "Vote to skip" : "Start a vote to skip");
    let volume = $derived(player.volume);
    let restore = $state(50);
    $effect(() => {
        if (player.volume > 0) restore = player.volume;
    });
    const VolumeIcon = $derived(
        volume === 0
            ? MaterialSymbolsVolumeOffRounded
            : volume < 34
              ? MaterialSymbolsVolumeMuteRounded
              : volume < 67
                ? MaterialSymbolsVolumeDownRounded
                : MaterialSymbolsVolumeUpRounded,
    );

    type Action = "previous" | "pause" | "next" | "shuffle" | "loop" | "autoplay" | "stop";
    let busy = $state<Action | null>(null);
    async function act(action: Action, run: () => ReturnType<typeof control>) {
        if (busy) return;
        busy = action;
        await run();
        busy = null;
    }
    const blocked = (action: Action) => busy !== null && busy !== action;

    async function setVolume(next: number) {
        volume = next;
        if (!(await control(music.setVolume({ guild, volume: next })))) volume = player.volume;
    }

    const loopNext = $derived(player.loop === "off" ? (queued ? "queue" : "track") : player.loop === "queue" ? "track" : "off");
    const LOOP_LABEL = { off: "Loop off", queue: "Looping the queue", track: "Looping this track" } as const;

    const icon = $derived([
        "ripple flex shrink-0 items-center justify-center rounded-full transition-colors disabled:opacity-40",
        mobile.current ? "size-12 [&_svg]:size-6" : "size-10 [&_svg]:size-5",
    ]);
    const toggle = (on: boolean) => [
        icon,
        on ? "bg-accent/10 text-accent hover:bg-accent/20" : "text-gray-400 hover:bg-gray-800 hover:text-gray-100",
    ];
    const tile = (on: boolean) => [
        "ripple flex h-14 w-full items-center gap-4 rounded-2xl px-4 text-sm font-medium transition-colors disabled:opacity-40 [&_svg]:size-6",
        on ? "bg-accent/10 text-accent hover:bg-accent/20" : "bg-gray-800 hover:bg-gray-700",
    ];
    let options = $state(false);
</script>

{#snippet progress()}
    {#if track && !track.isStream}
        <WavyProgress
            value={track.lengthMs ? position / track.lengthMs : 0}
            playing={!player.paused}
            bind:seeking
            step={5000 / Math.max(track.lengthMs, 1)}
            valuetext="{time(position)} of {time(track.lengthMs)}"
            onseek={lock ? undefined : (value) => onseek(Math.round(value * track.lengthMs))}
        />
    {:else}
        <WavyProgress value={track ? 1 : 0} live={!!track} {playing} label={track ? "Live stream" : "Nothing playing"} />
    {/if}
{/snippet}

{#snippet elapsed()}
    {#if track}
        <span class={[seeking !== null && "text-accent"]}>{time(seeking === null ? position : seeking * track.lengthMs)}</span>
    {:else}
        0:00
    {/if}
{/snippet}

{#snippet total()}
    {track ? (track.isStream ? "Live" : time(track.lengthMs)) : "0:00"}
{/snippet}

{#snippet previous()}
    <Tooltip content={(track && lock) || "Previous"}>
        <button
            type="button"
            aria-busy={busy === "previous"}
            disabled={!track || !!lock || blocked("previous")}
            class={[icon, "text-gray-100 hover:bg-gray-800"]}
            {@attach ripple}
            onclick={() => act("previous", () => control(music.previousTrack({ guild })))}
        >
            {#if busy === "previous"}<SvgSpinners90RingWithBg />{:else}<MaterialSymbolsSkipPreviousRounded />{/if}
        </button>
    </Tooltip>
{/snippet}

{#snippet pause()}
    <Tooltip content={(track && lock) || (playing ? "Pause" : "Play")}>
        <button
            type="button"
            aria-busy={busy === "pause"}
            disabled={!track || !!lock || blocked("pause")}
            class={[
                "ripple flex items-center justify-center bg-accent text-cyan-950 hover:bg-cyan-300 disabled:opacity-40",
                "transition-[border-radius] duration-400 ease-spring",
                mobile.current ? "h-16 w-20" : "h-12 w-16",
                playing ? "rounded-4xl" : "rounded-2xl",
            ]}
            {@attach ripple}
            onclick={() => act("pause", () => control(music.setPaused({ guild, paused: !player.paused })))}
        >
            {#if busy === "pause"}<SvgSpinners90RingWithBg class="size-6" />{:else if playing}<MaterialSymbolsPauseRounded
                    class={mobile.current ? "size-8" : "size-7"}
                />{:else}<MaterialSymbolsPlayArrowRounded class={mobile.current ? "size-8" : "size-7"} />{/if}
        </button>
    </Tooltip>
{/snippet}

{#snippet next()}
    <Tooltip content={(track && skip.lock) || skipLabel}>
        <!-- The badge sits beside the button, which clips anything outside it for the ripple -->
        <span class="relative flex">
            <button
                type="button"
                aria-busy={busy === "next"}
                disabled={!track || !!skip.lock || blocked("next")}
                class={[icon, "text-gray-100 hover:bg-gray-800"]}
                {@attach ripple}
                onclick={() => act("next", () => control(music.skipTrack({ guild })))}
            >
                {#if busy === "next"}<SvgSpinners90RingWithBg />{:else}<MaterialSymbolsSkipNextRounded />{/if}
            </button>
            {#if player.vote}
                <span
                    aria-hidden="true"
                    class="pointer-events-none absolute -top-1 -right-2 rounded-full bg-accent px-1.5 font-mono text-2xs leading-4 font-semibold text-cyan-950"
                >
                    {player.vote.voterIds.length}/{player.vote.needed}
                </span>
            {/if}
        </span>
    </Tooltip>
{/snippet}

{#snippet shuffle()}
    <Tooltip content={shuffleLock ?? (player.shuffle ? "Shuffle on" : "Shuffle off")}>
        <button
            type="button"
            aria-pressed={player.shuffle}
            class={toggle(player.shuffle)}
            {@attach ripple}
            aria-busy={busy === "shuffle"}
            disabled={!!shuffleLock || blocked("shuffle")}
            onclick={() => act("shuffle", () => control(music.setShuffle({ guild, enabled: !player.shuffle })))}
        >
            {#if busy === "shuffle"}<SvgSpinners90RingWithBg />{:else}<MaterialSymbolsShuffleRounded />{/if}
        </button>
    </Tooltip>
{/snippet}

{#snippet loop()}
    <Tooltip content={idle ?? LOOP_LABEL[player.loop]}>
        <button
            type="button"
            aria-pressed={player.loop !== "off"}
            class={toggle(player.loop !== "off")}
            {@attach ripple}
            aria-busy={busy === "loop"}
            disabled={!!idle || blocked("loop")}
            onclick={() => act("loop", () => control(music.setLoop({ guild, mode: loopNext })))}
        >
            {#if busy === "loop"}<SvgSpinners90RingWithBg />{:else if player.loop === "track"}<MaterialSymbolsRepeatOneRounded
                />{:else}<MaterialSymbolsRepeatRounded />{/if}
        </button>
    </Tooltip>
{/snippet}

{#snippet mute()}
    <Tooltip content={idle ?? (volume === 0 ? "Unmute" : "Mute")}>
        <button
            type="button"
            aria-pressed={volume === 0}
            disabled={!!idle}
            class={[icon, volume === 0 ? "text-red-400 hover:bg-red-400/10" : "text-gray-400 hover:bg-gray-800 hover:text-gray-100"]}
            {@attach ripple}
            onclick={() => setVolume(volume === 0 ? restore : 0)}
        >
            <VolumeIcon />
        </button>
    </Tooltip>
{/snippet}

{#if mobile.current}
    <section aria-label="Player controls" class="flex shrink-0 flex-col gap-2 rounded-3xl bg-gray-900 px-4 pt-2 pb-4">
        {@render progress()}
        <div class="flex justify-between font-mono text-xs text-gray-400">
            <span>{@render elapsed()}</span><span>{@render total()}</span>
        </div>
        <div class="flex items-center justify-between">
            {@render shuffle()}
            {@render previous()}
            {@render pause()}
            {@render next()}
            {@render loop()}
        </div>
    </section>

    <nav aria-label="Player" class="flex shrink-0 items-center justify-around rounded-full bg-gray-900 p-1">
        {@render dock?.()}
        <Tooltip content="More">
            <Drawer bind:open={options} title="More" triggerClass={[icon, "text-gray-400 hover:bg-gray-800 hover:text-gray-100"]}>
                {#snippet trigger()}<MaterialSymbolsMoreHorizRounded />{/snippet}
                <div class="flex flex-col gap-4">
                    <div class="flex items-center gap-2">
                        {@render mute()}
                        <Slider label="Volume" min={0} max={100} disabled={!!idle} bind:value={volume} onchange={setVolume} class="flex-1" />
                        <span class="w-8 text-right font-mono text-xs text-gray-400">{volume}</span>
                    </div>
                    <div class="grid grid-cols-2 gap-2">
                        <Tooltip content={idle} class="w-full">
                            <button
                                type="button"
                                aria-pressed={player.autoplay}
                                aria-busy={busy === "autoplay"}
                                disabled={!!idle || blocked("autoplay")}
                                class={tile(player.autoplay)}
                                {@attach ripple}
                                onclick={() => act("autoplay", () => control(music.setAutoplay({ guild, enabled: !player.autoplay })))}
                            >
                                {#if busy === "autoplay"}<SvgSpinners90RingWithBg />{:else}<MaterialSymbolsAutoplayRounded />{/if}
                                Autoplay
                            </button>
                        </Tooltip>
                        <Equalizer {guild} {player} lock={idle} labeled triggerClass={tile(player.eq.length > 0)} />
                    </div>
                    {#if track}
                        <Tooltip content={lock} class="w-full">
                            <button
                                type="button"
                                aria-busy={busy === "stop"}
                                disabled={!!lock || blocked("stop")}
                                class="ripple flex h-12 w-full items-center justify-center gap-2 rounded-full bg-red-400/10 text-sm font-medium text-red-400 transition-colors hover:bg-red-400/20 disabled:opacity-40 [&_svg]:size-5"
                                {@attach ripple}
                                onclick={() => act("stop", () => control(music.stopPlayer({ guild })))}
                            >
                                {#if busy === "stop"}<SvgSpinners90RingWithBg />{:else}<MaterialSymbolsStopRounded />{/if}
                                Stop and leave
                            </button>
                        </Tooltip>
                    {/if}
                </div>
            </Drawer>
        </Tooltip>
    </nav>
{:else}
    <section aria-label="Player controls" class="flex flex-col gap-2 rounded-3xl bg-gray-900 px-6 pt-2 pb-4">
        {@render progress()}
        <div class="flex items-center gap-4">
            <div class="flex shrink-0 items-center gap-2">
                {@render previous()}
                {@render pause()}
                {@render next()}
                <span class="pl-2 font-mono text-xs text-gray-400">{@render elapsed()} / {@render total()}</span>
            </div>

            <div class="ml-auto flex shrink-0 items-center gap-1">
                {@render shuffle()}
                {@render loop()}
                <Tooltip content={idle ?? (player.autoplay ? "Autoplay on" : "Autoplay off")}>
                    <button
                        type="button"
                        aria-pressed={player.autoplay}
                        class={toggle(player.autoplay)}
                        {@attach ripple}
                        aria-busy={busy === "autoplay"}
                        disabled={!!idle || blocked("autoplay")}
                        onclick={() => act("autoplay", () => control(music.setAutoplay({ guild, enabled: !player.autoplay })))}
                    >
                        {#if busy === "autoplay"}<SvgSpinners90RingWithBg />{:else}<MaterialSymbolsAutoplayRounded />{/if}
                    </button>
                </Tooltip>
                <Equalizer {guild} {player} lock={idle} triggerClass={toggle(player.eq.length > 0)} />
                <div class="flex items-center gap-1 pl-2">
                    {@render mute()}
                    <Slider label="Volume" min={0} max={100} disabled={!!idle} bind:value={volume} onchange={setVolume} class="w-24" />
                </div>
                {#if track}
                    <Tooltip content={lock ?? "Stop and leave"}>
                        <button
                            type="button"
                            class={[icon, "text-red-400 hover:bg-red-400/10"]}
                            {@attach ripple}
                            aria-busy={busy === "stop"}
                            disabled={!!lock || blocked("stop")}
                            onclick={() => act("stop", () => control(music.stopPlayer({ guild })))}
                        >
                            {#if busy === "stop"}<SvgSpinners90RingWithBg />{:else}<MaterialSymbolsStopRounded />{/if}
                        </button>
                    </Tooltip>
                {/if}
            </div>
        </div>
    </section>
{/if}
