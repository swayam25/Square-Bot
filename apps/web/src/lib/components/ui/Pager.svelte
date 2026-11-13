<script lang="ts">
    import Button from "#lib/components/ui/Button.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import MaterialSymbolsChevronLeftRounded from "~icons/material-symbols/chevron-left-rounded";
    import MaterialSymbolsChevronRightRounded from "~icons/material-symbols/chevron-right-rounded";

    let { page, pages, onpage }: { page: number; pages: number; onpage: (page: number) => void } = $props();
</script>

{#if pages > 1}
    <span class="text-sm text-gray-400">Page {page} of {pages}</span>
    <Tooltip content="Previous page">
        <Button variant="ghost" icon disabled={page <= 1} onclick={() => onpage(page - 1)}><MaterialSymbolsChevronLeftRounded /></Button>
    </Tooltip>
    <Tooltip content="Next page">
        <Button variant="ghost" icon disabled={page >= pages} onclick={() => onpage(page + 1)}><MaterialSymbolsChevronRightRounded /></Button>
    </Tooltip>
{/if}
