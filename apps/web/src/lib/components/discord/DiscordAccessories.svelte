<script lang="ts">
    import type { Snippet } from "svelte";

    let { children }: { children: Snippet } = $props();
</script>

<div class="grid justify-items-start gap-1 py-0.5 empty:hidden">{@render children()}</div>
