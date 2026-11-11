<script lang="ts">
    import Chip from "#lib/components/Chip.svelte";
    import WavyProgress from "#lib/components/WavyProgress.svelte";
    import { ripple } from "#lib/motion.ts";
    import TablerPlayerPauseFilled from "~icons/tabler/player-pause-filled";
    import TablerPlayerPlayFilled from "~icons/tabler/player-play-filled";
    import TablerPlayerSkipBackFilled from "~icons/tabler/player-skip-back-filled";
    import TablerPlayerSkipForwardFilled from "~icons/tabler/player-skip-forward-filled";
    import TablerVolume from "~icons/tabler/volume";

    // A self-contained preview of the web player for the home page: nothing here talks to the bot
    const LENGTH = 252;
    let elapsed = $state(161);
    let playing = $state(true);
    let filters = $state(["Bass Boost"]);
    let seeking = $state<number | null>(null);

    $effect(() => {
        if (!playing) return;
        const timer = setInterval(() => (elapsed = (elapsed + 1) % LENGTH), 1000);
        return () => clearInterval(timer);
    });

    const time = (seconds: number) => `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;

    function toggleFilter(name: string) {
        filters = filters.includes(name) ? filters.filter((filter) => filter !== name) : [...filters, name];
    }
</script>

<section aria-label="Preview of the web player" class="flex w-full max-w-md flex-col gap-6 rounded-4xl bg-surface-1 p-6 shadow-2xl shadow-black/40">
    <div class="flex items-center gap-4">
        <svg viewBox="0 0 200 200" aria-hidden="true" class="size-20 shrink-0 rounded-2xl">
            <rect width="200" height="200" fill="#1E1A4D" />
            <circle cx="140" cy="60" r="70" fill="#1FCEEC" />
            <rect y="100" width="110" height="110" rx="26" fill="#FF6900" />
            <circle cx="130" cy="160" r="36" fill="#8E51FF" />
        </svg>
        <div class="flex min-w-0 flex-col gap-1">
            <span class="truncate font-display text-xl font-semibold">Midnight Signals</span>
            <span class="truncate text-sm text-mist-400">Neon Harbor</span>
        </div>
    </div>

    <div class="flex flex-col gap-2">
        <WavyProgress
            value={elapsed / LENGTH}
            {playing}
            bind:seeking
            step={5 / LENGTH}
            valuetext="{time(elapsed)} of {time(LENGTH)}"
            onseek={(value) => (elapsed = Math.min(LENGTH - 1, Math.round(value * LENGTH)))}
        />
        <div class="flex justify-between font-mono text-xs text-mist-400">
            <span class={[seeking !== null && "text-accent"]}>{time(seeking === null ? elapsed : Math.round(seeking * LENGTH))}</span>
            <span>{time(LENGTH)}</span>
        </div>
    </div>

    <div class="flex items-center justify-center gap-4">
        <button
            type="button"
            aria-label="Previous"
            class="ripple flex size-12 items-center justify-center rounded-full bg-surface-2 hover:bg-surface-3"
            {@attach ripple}
        >
            <TablerPlayerSkipBackFilled class="size-5" />
        </button>
        <button
            type="button"
            aria-label={playing ? "Pause" : "Play"}
            onclick={() => (playing = !playing)}
            {@attach ripple}
            class={[
                "ripple flex h-14 w-20 items-center justify-center bg-accent text-cyan-950 hover:bg-cyan-300",
                // Squarer while paused, a pill while playing: the shape says the state before the icon does
                "transition-[border-radius] duration-400 ease-spring",
                playing ? "rounded-4xl" : "rounded-2xl",
            ]}
        >
            {#if playing}<TablerPlayerPauseFilled class="size-6" />{:else}<TablerPlayerPlayFilled class="size-6" />{/if}
        </button>
        <button
            type="button"
            aria-label="Next"
            class="ripple flex size-12 items-center justify-center rounded-full bg-surface-2 hover:bg-surface-3"
            {@attach ripple}
        >
            <TablerPlayerSkipForwardFilled class="size-5" />
        </button>
    </div>

    <div class="flex flex-wrap gap-2">
        <Chip><TablerVolume />80%</Chip>
        {#each ["Bass Boost", "Nightcore", "8D"] as name (name)}
            <button
                type="button"
                aria-pressed={filters.includes(name)}
                class="ripple rounded-full"
                onclick={() => toggleFilter(name)}
                {@attach ripple}
            >
                <Chip tone={filters.includes(name) ? "violet" : "muted"}>{name}</Chip>
            </button>
        {/each}
    </div>
</section>
