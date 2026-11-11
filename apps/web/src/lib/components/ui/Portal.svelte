<script lang="ts">
    import type { Snippet } from "svelte";

    let { children }: { children: Snippet } = $props();

    // Not Ark's Portal: it mounts a separate root that reads stale page data during navigation and crashes (sveltejs/svelte#19109)
    function portal(node: HTMLElement) {
        document.body.append(node);
        return () => node.remove();
    }
</script>

<div class="contents" {@attach portal}>{@render children()}</div>
