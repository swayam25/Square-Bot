<script lang="ts">
    import TableSkeleton from "#lib/components/TableSkeleton.svelte";

    let {
        tabs = false,
        table,
        groups = [{ rows: 3 }],
    }: { tabs?: boolean; table?: "search" | "filter"; groups?: { rows: number; title?: boolean }[] } = $props();

    const widths = [56, 40, 64, 48, 36];
</script>

<div aria-hidden="true" class="flex flex-col gap-6">
    {#if tabs}
        <div class="flex h-12 items-center gap-8 border-b border-white/10 px-4">
            <span class="h-4 w-24 skeleton rounded-full"></span>
            <span class="h-4 w-20 skeleton rounded-full"></span>
        </div>
    {/if}
    {#if table}
        <TableSkeleton toolbar={table} />
    {:else}
        {#each groups as { rows, title = true }, g (g)}
            <div class="flex flex-col gap-2">
                {#if title}<div class="flex h-7 items-center px-2"><span class="h-4 w-40 skeleton rounded-full"></span></div>{/if}
                <div class="flex flex-col divide-y divide-white/5 rounded-3xl bg-surface-1">
                    {#each { length: rows }, i (i)}
                        <div class="flex flex-col gap-4 p-4 md:flex-row md:items-center">
                            <div class="flex min-w-0 flex-1 items-center gap-4">
                                <span class="size-10 shrink-0 skeleton rounded-xl"></span>
                                <span class="flex flex-1 flex-col gap-2">
                                    <span class="h-4 w-32 skeleton rounded-full"></span>
                                    <span class="h-4 skeleton rounded-full" style:width="{widths[(g + i) % widths.length]}%"></span>
                                </span>
                            </div>
                            <span class="h-12 skeleton rounded-full md:h-10 md:w-80 md:shrink-0"></span>
                        </div>
                    {/each}
                </div>
            </div>
        {/each}
    {/if}
</div>
