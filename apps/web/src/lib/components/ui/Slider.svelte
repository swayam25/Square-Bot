<script lang="ts">
    import type { ClassValue } from "svelte/elements";

    let {
        value = $bindable(0),
        min = 0,
        max = 100,
        step = 1,
        label,
        disabled = false,
        onchange,
        class: className,
    }: {
        value?: number;
        min?: number;
        max?: number;
        step?: number;
        label: string;
        disabled?: boolean;
        onchange?: (value: number) => void;
        class?: ClassValue;
    } = $props();

    const progress = $derived((value - min) / Math.max(max - min, 1));
</script>

<!-- The real range input stays on top, invisible, so pointer, touch, keys and screen readers all work natively -->
<div class={["slider relative h-6", className]} style:--p={progress}>
    <input type="range" {min} {max} {step} aria-label={label} {disabled} bind:value onchange={() => onchange?.(value)} />
    <span class="fill" aria-hidden="true"></span>
    <span class="rest" aria-hidden="true"></span>
    <span class="handle" aria-hidden="true"></span>
</div>

<style>
    @property --gap {
        syntax: "<length>";
        inherits: true;
        initial-value: 0px;
    }

    .slider {
        --x: calc(var(--p) * (100% - 4px) + 2px);
        --fill: var(--color-gray-100);
        --gap: 0px;
        transition: --gap 400ms var(--ease-spring);
    }
    .slider:has(input:enabled:hover, input:enabled:active, input:focus-visible) {
        --gap: 6px;
    }
    .slider:has(input:focus-visible) {
        --fill: var(--color-accent);
    }
    .slider:has(input:disabled) {
        opacity: 0.4;
    }

    input {
        position: absolute;
        inset: 0;
        z-index: 1;
        width: 100%;
        margin: 0;
        cursor: pointer;
        opacity: 0;
        appearance: none;
    }
    input:disabled {
        cursor: default;
    }
    input::-webkit-slider-thumb {
        appearance: none;
        width: 4px;
        height: 24px;
    }
    input::-moz-range-thumb {
        width: 4px;
        height: 24px;
        border: none;
    }

    .fill,
    .rest,
    .handle {
        position: absolute;
        top: 50%;
        border-radius: 999px;
        pointer-events: none;
        translate: 0 -50%;
    }
    .fill {
        left: 0;
        width: max(0px, calc(var(--x) - var(--gap)));
        height: 4px;
        background: var(--fill);
        transition: background-color 200ms ease-out;
    }
    .rest {
        left: calc(var(--x) + var(--gap));
        right: 0;
        height: 4px;
        background: rgb(255 255 255 / 0.1);
    }
    .handle {
        left: calc(var(--x) - 2px);
        width: 4px;
        height: 20px;
        background: var(--fill);
        opacity: 0;
        scale: 1 0;
        transition:
            scale 400ms var(--ease-spring),
            opacity 200ms ease-out,
            background-color 200ms ease-out;
    }
    .slider:has(input:enabled:hover, input:enabled:active, input:focus-visible) .handle {
        opacity: 1;
        scale: 1 1;
    }
</style>
