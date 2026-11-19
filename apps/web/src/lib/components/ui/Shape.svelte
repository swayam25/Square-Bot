<script lang="ts">
    import { blobPath } from "#lib/shape.ts";
    import type { ClassValue } from "svelte/elements";

    let { lobes = 12, depth = 0.06, class: className }: { lobes?: number; depth?: number; class?: ClassValue } = $props();

    const path = $derived(blobPath(lobes, depth));
</script>

<svg viewBox="0 0 100 100" aria-hidden="true" class={className}><path d={path} fill="currentColor" /></svg>
