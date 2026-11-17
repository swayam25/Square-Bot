<script lang="ts">
    let { rows = 6, toolbar }: { rows?: number; toolbar?: "search" | "filter" } = $props();

    const widths = [44, 32, 52, 38, 48, 28];
</script>

<div aria-hidden="true" class="flex flex-col gap-4">
    {#if toolbar === "search"}
        <div class="flex flex-wrap justify-end gap-2">
            <span class="h-12 w-full skeleton rounded-control-lg sm:w-64 md:h-10 md:rounded-2xl"></span>
            <span class="h-12 w-32 shrink-0 skeleton rounded-control-lg md:h-10 md:rounded-2xl"></span>
        </div>
    {:else if toolbar === "filter"}
        <div class="flex flex-wrap gap-2">
            <span class="h-12 w-80 max-w-full skeleton rounded-control-lg md:h-10 md:rounded-2xl"></span>
            <span class="h-12 min-w-60 flex-1 skeleton rounded-control-lg md:h-10 md:rounded-2xl"></span>
            <span class="size-12 shrink-0 skeleton rounded-control-lg md:size-10 md:rounded-2xl"></span>
        </div>
    {/if}
    <div class="flex flex-col divide-y divide-white/5 rounded-card bg-gray-900">
        <div class="flex h-10 items-center gap-8 px-4">
            <span class="h-2 w-16 skeleton rounded-sm"></span>
            <span class="h-2 w-12 skeleton rounded-sm"></span>
            <span class="ml-auto h-2 w-12 skeleton rounded-sm"></span>
        </div>
        {#each { length: rows }, i (i)}
            <div class="flex h-14 items-center gap-4 px-4">
                <span class="size-8 shrink-0 skeleton rounded-icon"></span>
                <span class="h-4 skeleton rounded-md" style:width="{widths[i % widths.length]}%"></span>
                <span class="ml-auto h-4 w-12 shrink-0 skeleton rounded-md"></span>
            </div>
        {/each}
    </div>
</div>
