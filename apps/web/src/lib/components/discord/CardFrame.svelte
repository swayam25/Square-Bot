<script lang="ts">
    import type { Snippet } from "svelte";

    let { children }: { children: Snippet } = $props();
</script>

<!-- The bot's `Kit.card` in imaging/components.py: 720px wide, square corners, since Discord rounds images itself -->
<div class="flex w-180 flex-col gap-6 bg-surface-1 p-6 font-sans text-gray-100">{@render children()}</div>
