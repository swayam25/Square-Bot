<script lang="ts">
    import Slider from "#lib/components/ui/Slider.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import WavyProgress from "#lib/components/ui/WavyProgress.svelte";
    import { time } from "#lib/format.ts";
    import { ripple } from "#lib/motion.ts";
    import * as music from "#lib/music.remote.ts";
    import type { PlayerState } from "@square/api-client";
    import MaterialSymbolsAutoplayRounded from "~icons/material-symbols/autoplay-rounded";
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
    }: {
        guild: string;
        player: PlayerState;
        access: Access;
        position: number;
        seeking?: number | null;
        onseek: (ms: number) => void;
    } = $props();

    const track = $derived(player.track);
    const playing = $derived(!!track && !player.paused);
    const lock = $derived(locked(access));
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

    function setVolume(next: number) {
        volume = next;
        return control(music.setVolume({ guild, volume: next }));
    }

    const LOOP_NEXT = { off: "queue", queue: "track", track: "off" } as const;
    const LOOP_LABEL = { off: "Loop off", queue: "Looping the queue", track: "Looping this track" } as const;

    const icon = "ripple flex size-10 shrink-0 items-center justify-center rounded-full transition-colors disabled:opacity-40 [&_svg]:size-5";
    const toggle = (on: boolean) => [
        icon,
        on ? "bg-accent/10 text-accent hover:bg-accent/20" : "text-mist-400 hover:bg-surface-2 hover:text-mist-100",
    ];
</script>

<section aria-label="Player controls" class="flex flex-col gap-2 rounded-3xl bg-surface-1 px-4 pt-2 pb-4 md:px-6">
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

    <div class="flex items-center gap-4 max-sm:flex-col max-sm:gap-2">
        <div class="flex shrink-0 items-center gap-2">
            <Tooltip content={track ? lock : null}>
                <button
                    type="button"
                    aria-label="Previous"
                    aria-busy={busy === "previous"}
                    disabled={!track || !!lock || blocked("previous")}
                    class={[icon, "text-mist-100 hover:bg-surface-2"]}
                    {@attach ripple}
                    onclick={() => act("previous", () => control(music.previousTrack({ guild })))}
                >
                    {#if busy === "previous"}<SvgSpinners90RingWithBg />{:else}<MaterialSymbolsSkipPreviousRounded />{/if}
                </button>
            </Tooltip>
            <Tooltip content={track ? lock : null}>
                <button
                    type="button"
                    aria-label={playing ? "Pause" : "Play"}
                    aria-busy={busy === "pause"}
                    disabled={!track || !!lock || blocked("pause")}
                    class={[
                        "ripple flex h-12 w-16 items-center justify-center bg-accent text-cyan-950 hover:bg-cyan-300 disabled:opacity-40",
                        "transition-[border-radius] duration-400 ease-spring",
                        playing ? "rounded-4xl" : "rounded-2xl",
                    ]}
                    {@attach ripple}
                    onclick={() => act("pause", () => control(music.setPaused({ guild, paused: !player.paused })))}
                >
                    {#if busy === "pause"}<SvgSpinners90RingWithBg class="size-6" />{:else if playing}<MaterialSymbolsPauseRounded
                            class="size-7"
                        />{:else}<MaterialSymbolsPlayArrowRounded class="size-7" />{/if}
                </button>
            </Tooltip>
            <Tooltip content={track ? (skip.lock ?? (skip.now ? null : skipLabel)) : null}>
                <!-- The badge sits beside the button, which clips anything outside it for the ripple -->
                <span class="relative flex">
                    <button
                        type="button"
                        aria-label={skipLabel}
                        aria-busy={busy === "next"}
                        disabled={!track || !!skip.lock || blocked("next")}
                        class={[icon, "text-mist-100 hover:bg-surface-2"]}
                        {@attach ripple}
                        onclick={() => act("next", () => control(music.skipTrack({ guild }), { announce: true }))}
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
            <span class="hidden pl-2 font-mono text-xs text-mist-400 sm:inline">
                {#if track}
                    <span class={[seeking !== null && "text-accent"]}>{time(seeking === null || !track ? position : seeking * track.lengthMs)}</span>
                    / {track.isStream ? "Live" : time(track.lengthMs)}
                {:else}
                    0:00 / 0:00
                {/if}
            </span>
        </div>

        <div class="ml-auto flex shrink-0 items-center gap-1 max-sm:ml-0 max-sm:w-full max-sm:justify-evenly">
            <Tooltip content={lock ?? (player.shuffle ? "Shuffle on" : "Shuffle off")}>
                <button
                    type="button"
                    aria-label="Shuffle"
                    aria-pressed={player.shuffle}
                    class={toggle(player.shuffle)}
                    {@attach ripple}
                    aria-busy={busy === "shuffle"}
                    disabled={!!lock || blocked("shuffle")}
                    onclick={() => act("shuffle", () => control(music.setShuffle({ guild, enabled: !player.shuffle })))}
                >
                    {#if busy === "shuffle"}<SvgSpinners90RingWithBg />{:else}<MaterialSymbolsShuffleRounded />{/if}
                </button>
            </Tooltip>
            <Tooltip content={lock ?? LOOP_LABEL[player.loop]}>
                <button
                    type="button"
                    aria-label={LOOP_LABEL[player.loop]}
                    aria-pressed={player.loop !== "off"}
                    class={toggle(player.loop !== "off")}
                    {@attach ripple}
                    aria-busy={busy === "loop"}
                    disabled={!!lock || blocked("loop")}
                    onclick={() => act("loop", () => control(music.setLoop({ guild, mode: LOOP_NEXT[player.loop] })))}
                >
                    {#if busy === "loop"}<SvgSpinners90RingWithBg />{:else if player.loop === "track"}<MaterialSymbolsRepeatOneRounded
                        />{:else}<MaterialSymbolsRepeatRounded />{/if}
                </button>
            </Tooltip>
            <Tooltip content={lock ?? (player.autoplay ? "Autoplay on" : "Autoplay off")}>
                <button
                    type="button"
                    aria-label="Autoplay"
                    aria-pressed={player.autoplay}
                    class={toggle(player.autoplay)}
                    {@attach ripple}
                    aria-busy={busy === "autoplay"}
                    disabled={!!lock || blocked("autoplay")}
                    onclick={() => act("autoplay", () => control(music.setAutoplay({ guild, enabled: !player.autoplay })))}
                >
                    {#if busy === "autoplay"}<SvgSpinners90RingWithBg />{:else}<MaterialSymbolsAutoplayRounded />{/if}
                </button>
            </Tooltip>
            <Equalizer {guild} {player} {lock} triggerClass={toggle(player.eq.length > 0)} />
            <div class="hidden items-center gap-1 pl-2 md:flex">
                <Tooltip content={lock ?? (volume === 0 ? "Unmute" : "Mute")}>
                    <button
                        type="button"
                        aria-label={volume === 0 ? "Unmute" : "Mute"}
                        aria-pressed={volume === 0}
                        disabled={!!lock}
                        class={[icon, volume === 0 ? "text-red-400 hover:bg-red-400/10" : "text-mist-400 hover:bg-surface-2 hover:text-mist-100"]}
                        {@attach ripple}
                        onclick={() => setVolume(volume === 0 ? restore : 0)}
                    >
                        <VolumeIcon />
                    </button>
                </Tooltip>
                <Slider label="Volume" min={0} max={100} disabled={!!lock} bind:value={volume} onchange={setVolume} class="w-24" />
            </div>
            {#if track}
                <Tooltip content={lock ?? "Stop and leave"}>
                    <button
                        type="button"
                        aria-label="Stop and leave"
                        class={[icon, "text-red-400 hover:bg-red-400/10"]}
                        {@attach ripple}
                        aria-busy={busy === "stop"}
                        disabled={!!lock || blocked("stop")}
                        onclick={() => act("stop", () => control(music.stopPlayer({ guild }), { announce: true }))}
                    >
                        {#if busy === "stop"}<SvgSpinners90RingWithBg />{:else}<MaterialSymbolsStopRounded />{/if}
                    </button>
                </Tooltip>
            {/if}
        </div>
    </div>
</section>
