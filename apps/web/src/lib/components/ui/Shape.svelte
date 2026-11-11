<script lang="ts">
    import type { ClassValue } from "svelte/elements";

    let { lobes = 12, depth = 0.06, class: className }: { lobes?: number; depth?: number; class?: ClassValue } = $props();

    const path = $derived.by(() => {
        const steps = Math.max(64, lobes * 16);
        const points: string[] = [];
        for (let step = 0; step < steps; step++) {
            const angle = (step / steps) * Math.PI * 2;
            const radius = (50 * (1 + depth * Math.cos(lobes * angle))) / (1 + depth);
            points.push(`${(50 + radius * Math.sin(angle)).toFixed(1)} ${(50 - radius * Math.cos(angle)).toFixed(1)}`);
        }
        return `M${points.join("L")}Z`;
    });
</script>

<svg viewBox="0 0 100 100" aria-hidden="true" class={className}><path d={path} fill="currentColor" /></svg>
