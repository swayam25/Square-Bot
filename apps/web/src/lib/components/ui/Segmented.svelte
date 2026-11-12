<script lang="ts" generics="T extends string">
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import type { Component } from "svelte";
    import type { ClassValue } from "svelte/elements";

    let {
        options,
        value = $bindable(),
        label,
        class: className,
        pill = "bg-surface-3",
    }: {
        // A disabled option says why in a tooltip
        options: { value: T; label: string; count?: number; icon?: Component; disabled?: string | false }[];
        value: T;
        label: string;
        class?: ClassValue;
        // The sliding indicator's fill, for tracks on a different background
        pill?: ClassValue;
    } = $props();

    let track = $state<HTMLDivElement>();
    const buttons: Record<string, HTMLElement> = $state({});
    let bar = $state<{ x: number; w: number } | null>(null);
    // The pill only animates after its first placement, so it doesn't slide in from the left edge on load
    let settled = $state(false);

    function measure() {
        const active = buttons[value];
        bar = active ? { x: active.offsetLeft, w: active.offsetWidth } : null;
    }

    $effect(() => {
        void value;
        void options.length;
        measure();
    });

    // Panels resize, so the pill follows the tab widths
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

<div bind:this={track} role="tablist" aria-label={label} class={["relative flex rounded-full bg-surface-2 p-1", className]}>
    {#if bar}
        <span
            aria-hidden="true"
            class={["pointer-events-none absolute inset-y-1 left-0 rounded-full", pill, settled && "slide"]}
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
                    "relative flex h-10 w-full items-center justify-center gap-2 rounded-full px-4 text-sm font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-40 md:h-8",
                    value === option.value ? "text-mist-50" : "text-mist-400 enabled:hover:text-mist-100",
                ]}
            >
                {#if option.icon}<option.icon class="size-4 shrink-0" />{/if}
                {option.label}
                {#if option.count}<span class="font-mono text-xs text-mist-400">{option.count}</span>{/if}
            </button>
        </Tooltip>
    {/each}
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
