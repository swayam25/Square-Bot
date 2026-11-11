<script lang="ts">
    import type { Snippet } from "svelte";

    let { children }: { children: Snippet } = $props();
</script>

<div class="@container w-full overflow-hidden rounded-lg">
    <div class="w-180" style="zoom: tan(atan2(100cqw, 720px))">{@render children()}</div>
</div>
