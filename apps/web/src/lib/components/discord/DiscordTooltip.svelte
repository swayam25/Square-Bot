<script lang="ts">
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import type { ComponentProps } from "svelte";

    let props: Omit<ComponentProps<typeof Tooltip>, "arrow" | "contentClass"> = $props();
</script>

<Tooltip
    {...props}
    arrow
    contentClass="max-w-47.5 rounded-lg border border-(--tooltip-border) bg-(--tooltip-bg) px-3 py-2 text-sm leading-4 font-medium text-dc-strong shadow-lg shadow-black/30 [--tooltip-bg:var(--color-dc-surface)] [--tooltip-border:var(--color-dc-border)]"
/>
