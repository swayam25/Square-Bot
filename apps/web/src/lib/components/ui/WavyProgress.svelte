<script lang="ts">
    import type { ClassValue } from "svelte/elements";
    import { prefersReducedMotion, Spring } from "svelte/motion";

    let {
        value,
        playing = true,
        live = false,
        label = "Seek",
        valuetext,
        step = 0.05,
        onseek,
        seeking = $bindable(null),
        class: className,
    }: {
        /** 0 to 1 */
        value: number;
        playing?: boolean;
        live?: boolean;
        label?: string;
        valuetext?: string;
        step?: number;
        onseek?: (value: number) => void;
        seeking?: number | null;
        class?: ClassValue;
    } = $props();

    const HEIGHT = 16;
    const MID = HEIGHT / 2;
    const AMPLITUDE = 3;
    const WAVELENGTH = 32;
    const GAP = 12;
    const HANDLE_GAP = 8;
    const FLOW = WAVELENGTH / 1200;

    let root = $state<HTMLDivElement>();
    let width = $state(0);
    let phase = $state(0);
    let hovered = $state(false);
    let focused = $state(false);

    const seekable = $derived(!!onseek && !live);
    const amplitude = new Spring(AMPLITUDE, { stiffness: 0.12, damping: 0.5 });
    const handle = new Spring(0, { stiffness: 0.2, damping: 0.6 });

    $effect(() => {
        const instant = prefersReducedMotion.current;
        amplitude.set((playing || live) && seeking === null ? AMPLITUDE : 0, { instant });
        handle.set(seekable && (hovered || focused || seeking !== null) ? 1 : 0, { instant });
    });

    const x = $derived(live ? width - 3 : 3 + Math.max(0, Math.min(1, seeking ?? value)) * (width - 6));
    const activeEnd = $derived(x - HANDLE_GAP * handle.current);
    const trackStart = $derived(x + GAP - (GAP - HANDLE_GAP) * handle.current);

    function line(from: number, to: number) {
        if (amplitude.current < 0.05) return `M${from} ${MID}H${to}`;
        let d = "";
        for (let at = from; at < to + 2; at += 2) {
            const point = Math.min(at, to);
            const y = MID - amplitude.current * Math.sin(((point + phase) / WAVELENGTH) * 2 * Math.PI);
            d += `${d ? "L" : "M"}${point.toFixed(1)} ${y.toFixed(2)}`;
        }
        return d;
    }

    $effect(() => {
        if (!(playing || live) || prefersReducedMotion.current) return;
        let last = performance.now();
        let frame = 0;
        const tick = (now: number) => {
            phase = (phase - (now - last) * FLOW) % WAVELENGTH;
            last = now;
            frame = requestAnimationFrame(tick);
        };
        frame = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(frame);
    });

    function at(event: PointerEvent) {
        const rect = root!.getBoundingClientRect();
        return Math.max(0, Math.min(1, (event.clientX - rect.left - 3) / (rect.width - 6)));
    }

    function release() {
        if (seeking === null) return;
        onseek?.(seeking);
        seeking = null;
    }

    function onkeydown(event: KeyboardEvent) {
        const moves: Record<string, number> = { ArrowLeft: -step, ArrowDown: -step, ArrowRight: step, ArrowUp: step, Home: -1, End: 1 };
        if (!(event.key in moves)) return;
        event.preventDefault();
        onseek?.(Math.max(0, Math.min(1, value + moves[event.key])));
    }
</script>

{#snippet bar()}
    {#if width}
        <svg {width} height={HEIGHT} class="pointer-events-none overflow-visible">
            {#if activeEnd >= 3 || live}
                <path
                    d={line(3, live ? x : activeEnd)}
                    fill="none"
                    class="stroke-accent"
                    stroke-width="5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                />
            {/if}
            {#if !live && trackStart < width - GAP}
                <path d="M{trackStart} {MID}H{width - GAP}" class="stroke-white/10" stroke-width="5" stroke-linecap="round" />
                <circle cx={width - 3} cy={MID} r="2.5" class="fill-accent" />
            {/if}
            {#if handle.current > 0.01}
                <rect
                    x={x - 2}
                    y={MID - 12 * handle.current}
                    width="4"
                    height={24 * handle.current}
                    rx="2"
                    opacity={Math.min(1, handle.current)}
                    class="fill-accent"
                />
            {/if}
        </svg>
    {/if}
{/snippet}

{#if seekable}
    <div
        bind:this={root}
        bind:clientWidth={width}
        role="slider"
        tabindex="0"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round((seeking ?? value) * 100)}
        aria-valuetext={valuetext}
        class={[
            "relative h-4 cursor-pointer touch-pan-y outline-none select-none",
            "before:absolute before:inset-x-0 before:-inset-y-4 focus-visible:before:rounded-full focus-visible:before:outline-2 focus-visible:before:outline-offset-2 focus-visible:before:outline-accent",
            className,
        ]}
        onpointerenter={(event) => event.pointerType === "mouse" && (hovered = true)}
        onpointerleave={() => (hovered = false)}
        onpointerdown={(event) => {
            if (event.button !== 0) return;
            root!.setPointerCapture(event.pointerId);
            seeking = at(event);
        }}
        onpointermove={(event) => seeking !== null && (seeking = at(event))}
        onpointerup={release}
        onpointercancel={() => (seeking = null)}
        onfocus={() => (focused = root!.matches(":focus-visible"))}
        onblur={() => (focused = false)}
        {onkeydown}
    >
        {@render bar()}
    </div>
{:else}
    <div bind:clientWidth={width} class={["h-4", className]} aria-hidden="true">
        {@render bar()}
    </div>
{/if}
