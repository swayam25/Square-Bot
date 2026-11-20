<script lang="ts" generics="T extends string">
    import { edgeFade } from "#lib/attachments/edge-fade.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { formatCount } from "#lib/format.ts";
    import type { Component } from "svelte";
    import type { ClassValue } from "svelte/elements";

    let {
        options,
        value = $bindable(),
        label,
        class: className,
        pill = "bg-gray-700",
    }: {
        options: { value: T; label: string; count?: number; icon?: Component; disabled?: string | false }[];
        value: T;
        label: string;
        class?: ClassValue;
        pill?: ClassValue;
    } = $props();

    const FADE = 32;

    let track = $state<HTMLDivElement>();
    const buttons: Record<string, HTMLElement> = $state({});
    let bar = $state<{ x: number; w: number } | null>(null);
    // The pill only animates after its first placement, so it doesn't slide in from the left edge on load
    let settled = $state(false);

    function measure() {
        const active = buttons[value];
        bar = active ? { x: active.offsetLeft, w: active.offsetWidth } : null;
    }

    // Too many options for the width scrolls the track, so the picked one is kept in view and clear of the fade
    function reveal() {
        const active = buttons[value];
        if (!track || !active) return;
        const left = active.offsetLeft - FADE;
        const right = active.offsetLeft + active.offsetWidth + FADE;
        if (left < track.scrollLeft) track.scrollLeft = left;
        else if (right > track.scrollLeft + track.clientWidth) track.scrollLeft = right - track.clientWidth;
    }

    $effect(() => {
        void value;
        void options.length;
        measure();
        reveal();
    });

    $effect(() => {
        if (!track) return;
        const observer = new ResizeObserver(measure);
        observer.observe(track);
        const frame = requestAnimationFrame(() => (settled = true));
        return () => {
            observer.disconnect();
            cancelAnimationFrame(frame);
        };
    });
</script>

<div class={["flex max-w-full rounded-control-lg bg-gray-800 md:rounded-2xl", className]}>
    <div
        bind:this={track}
        role="tablist"
        aria-label={label}
        class="edge-fade-x relative flex min-w-0 flex-1 scrollbar-none overflow-x-auto overscroll-x-contain rounded-[inherit] p-1 [&::-webkit-scrollbar]:hidden"
        {@attach edgeFade("x")}
    >
        {#if bar}
            <span
                aria-hidden="true"
                class={["pointer-events-none absolute inset-y-1 left-0 rounded-2xl md:rounded-xl", pill, settled && "slide"]}
                style="width: {bar.w}px; transform: translateX({bar.x}px)"
            ></span>
        {/if}
        {#each options as option (option.value)}
            <Tooltip content={option.disabled || null} class="flex-1">
                <button
                    bind:this={buttons[option.value]}
                    type="button"
                    role="tab"
                    aria-selected={value === option.value}
                    disabled={!!option.disabled}
                    onclick={() => (value = option.value)}
                    class={[
                        "relative flex h-10 w-full items-center justify-center gap-2 rounded-2xl px-3 text-sm font-medium whitespace-nowrap transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-40 md:h-8 md:gap-1.5 md:rounded-xl",
                        value === option.value ? "text-gray-50" : "text-gray-400 enabled:hover:text-gray-100",
                    ]}
                >
                    {#if option.icon}<option.icon class="size-5 shrink-0 md:size-4.5" />{/if}
                    {option.label}
                    {#if option.count}<span class="font-mono text-xs text-gray-400">{formatCount(option.count)}</span>{/if}
                </button>
            </Tooltip>
        {/each}
    </div>
</div>

<style>
    .slide {
        transition:
            transform 450ms var(--ease-spring),
            width 450ms var(--ease-spring);
    }

    @media (prefers-reduced-motion: reduce) {
        .slide {
            transition: none;
        }
    }
</style>
