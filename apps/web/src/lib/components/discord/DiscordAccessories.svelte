<script lang="ts">
    import type { Snippet } from "svelte";

    let { children }: { children: Snippet } = $props();
</script>

<div class="grid grid-cols-1 justify-items-start gap-1 py-0.5 empty:hidden">{@render children()}</div>
