<script lang="ts">
    import Chip from "#lib/components/ui/Chip.svelte";
    import ScrollRow from "#lib/components/ui/ScrollRow.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import WavyProgress from "#lib/components/ui/WavyProgress.svelte";
    import { demo, time } from "#lib/demo.svelte.ts";
    import { ripple } from "#lib/motion.ts";
    import MaterialSymbolsPauseRounded from "~icons/material-symbols/pause-rounded";
    import MaterialSymbolsPlayArrowRounded from "~icons/material-symbols/play-arrow-rounded";
    import MaterialSymbolsSkipNextRounded from "~icons/material-symbols/skip-next-rounded";
    import MaterialSymbolsSkipPreviousRounded from "~icons/material-symbols/skip-previous-rounded";
    import MaterialSymbolsVolumeUpRounded from "~icons/material-symbols/volume-up-rounded";

    let seeking = $state<number | null>(null);

    $effect(() => demo.attach());
</script>

<section aria-label="Preview of the web player" class="flex w-full max-w-md flex-col gap-6 rounded-4xl bg-surface-1 p-6 shadow-2xl shadow-black/40">
    <div class="flex items-center gap-4">
        <img src={demo.track.artwork} alt="" class="size-20 shrink-0 rounded-2xl bg-surface-2 object-cover" />
        <div class="flex min-w-0 flex-col gap-1">
            <span class="truncate font-display text-xl font-semibold">{demo.track.title}</span>
            <span class="truncate text-sm text-gray-400">{demo.track.author}</span>
        </div>
    </div>

    <div class="flex flex-col gap-2">
        <WavyProgress
            value={demo.elapsed / demo.track.duration}
            playing={demo.playing}
            bind:seeking
            step={5 / demo.track.duration}
            valuetext="{time(demo.elapsed)} of {time(demo.track.duration)}"
            onseek={(value) => demo.seek(value * demo.track.duration)}
        />
        <div class="flex justify-between font-mono text-xs text-gray-400">
            <span class={[seeking !== null && "text-accent"]}>{time(seeking === null ? demo.elapsed : seeking * demo.track.duration)}</span>
            <span>{time(demo.track.duration)}</span>
        </div>
    </div>

    <div class="flex items-center justify-center gap-4">
        <Tooltip content="Previous">
            <button
                type="button"
                onclick={() => demo.previous()}
                class="ripple flex size-12 items-center justify-center rounded-full bg-surface-2 hover:bg-surface-3"
                {@attach ripple}
            >
                <MaterialSymbolsSkipPreviousRounded class="size-5" />
            </button>
        </Tooltip>
        <Tooltip content={demo.playing ? "Pause" : "Play"}>
            <button
                type="button"
                onclick={() => demo.toggle()}
                {@attach ripple}
                class={[
                    "ripple flex h-14 w-20 items-center justify-center bg-accent text-cyan-950 hover:bg-cyan-300",
                    "transition-[border-radius] duration-400 ease-spring",
                    demo.playing ? "rounded-4xl" : "rounded-2xl",
                ]}
            >
                {#if demo.playing}<MaterialSymbolsPauseRounded class="size-6" />{:else}<MaterialSymbolsPlayArrowRounded class="size-6" />{/if}
            </button>
        </Tooltip>
        <Tooltip content="Next">
            <button
                type="button"
                onclick={() => demo.skip()}
                class="ripple flex size-12 items-center justify-center rounded-full bg-surface-2 hover:bg-surface-3"
                {@attach ripple}
            >
                <MaterialSymbolsSkipNextRounded class="size-5" />
            </button>
        </Tooltip>
    </div>

    <ScrollRow>
        <Chip><MaterialSymbolsVolumeUpRounded />80%</Chip>
        {#each ["Bass Boost", "Nightcore", "8D"] as name (name)}
            <button
                type="button"
                aria-pressed={demo.filters.includes(name)}
                class="ripple rounded-full"
                onclick={() => demo.toggleFilter(name)}
                {@attach ripple}
            >
                <Chip tone={demo.filters.includes(name) ? "violet" : "muted"}>{name}</Chip>
            </button>
        {/each}
    </ScrollRow>
</section>
