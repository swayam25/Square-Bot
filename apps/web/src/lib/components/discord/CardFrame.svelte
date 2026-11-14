<script lang="ts">
    import type { Snippet } from "svelte";

    let { children }: { children: Snippet } = $props();
</script>

<div class="flex w-180 flex-col gap-6 bg-gray-950 p-6 font-sans text-gray-100">{@render children()}</div>
