<script lang="ts">
    import type { ClassValue } from "svelte/elements";

    type Part = { value: number; label: string; class: string };

    let { parts, label, class: className }: { parts: Part[]; label?: string; class?: ClassValue } = $props();

    const shown = $derived(parts.filter((part) => part.value > 0));
</script>

<div
    role="img"
    aria-label={shown.map((part) => `${part.label} ${part.value}`).join(", ")}
    class={["flex h-10 gap-1 rounded-full bg-gray-900 p-1", className]}
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
