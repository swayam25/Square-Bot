<script lang="ts">
    import type { ClassValue } from "svelte/elements";

    type Part = { value: number; label: string; class: string };

    let { parts, label, class: className }: { parts: Part[]; label?: string; class?: ClassValue } = $props();

    const shown = $derived(parts.filter((part) => part.value > 0));
</script>

<!--
    The spec's thick split bar: parts sized by value with a 24px floor, outer ends rounded to half the 32px inner height
    and inner corners `rounded-lg`. The label is offset with margin, since padding would skew the flex shares.
-->
<div
    role="img"
    aria-label={shown.map((part) => `${part.label} ${part.value}`).join(", ")}
    class={["flex h-10 gap-1 rounded-full bg-surface-2 p-1", className]}
>
    {#each shown as part, index (part.label)}
        <div
            class={["flex min-w-6 items-center rounded-lg first:rounded-l-2xl last:rounded-r-2xl", "origin-left animate-grow", part.class]}
            style="flex: {part.value}; animation-delay: {index * 60}ms"
        >
            {#if index === 0 && label}
                <span class="ml-4 font-mono text-xs font-semibold text-cyan-950 uppercase">{label}</span>
            {/if}
        </div>
    {/each}
</div>
