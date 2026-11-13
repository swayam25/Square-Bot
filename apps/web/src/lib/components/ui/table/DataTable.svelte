<script lang="ts" generics="T extends RowData">
    import Checkbox from "#lib/components/ui/Checkbox.svelte";
    import { createTable, FlexRender, type RowData, type RowSelectionState, type SortingState, type Updater } from "@tanstack/svelte-table";
    import MaterialSymbolsArrowDownwardRounded from "~icons/material-symbols/arrow-downward-rounded";
    import MaterialSymbolsArrowUpwardRounded from "~icons/material-symbols/arrow-upward-rounded";
    import { features, type TableColumn } from "./features.ts";

    let {
        data,
        columns,
        getRowId,
        label,
        sorting = $bindable([]),
        manualSorting = false,
        selectable = false,
        rowSelection = $bindable({}),
        active = null,
        onrowclick,
    }: {
        data: T[];
        columns: TableColumn<T>[];
        getRowId: (row: T) => string;
        label: string;
        sorting?: SortingState;
        manualSorting?: boolean;
        selectable?: boolean;
        rowSelection?: RowSelectionState;
        active?: string | null;
        onrowclick?: (row: T) => void;
    } = $props();

    const resolve = <S,>(updater: Updater<S>, previous: S): S =>
        typeof updater === "function" ? (updater as (previous: S) => S)(previous) : updater;

    const table = createTable({
        features,
        get data() {
            return data;
        },
        get columns() {
            return columns;
        },
        getRowId: (row) => getRowId(row),
        get manualSorting() {
            return manualSorting;
        },
        sortDescFirst: true,
        enableMultiSort: false,
        state: {
            get sorting() {
                return sorting;
            },
            get rowSelection() {
                return rowSelection;
            },
        },
        onSortingChange: (updater) => (sorting = resolve(updater, sorting)),
        onRowSelectionChange: (updater) => (rowSelection = resolve(updater, rowSelection)),
    });

    const rows = $derived(table.getRowModel().rows);
    const aligned = (align: "start" | "end" | undefined) => (align === "end" ? "text-right" : "text-left");
</script>

<!-- A container, so columns hide by the table's own width: a side panel can squeeze it at any window size -->
<div class="@container overflow-x-auto rounded-3xl bg-surface-1">
    <table aria-label={label} class="w-full table-fixed border-collapse text-sm">
        <thead>
            {#each table.getHeaderGroups() as group (group.id)}
                <tr class="border-b border-white/5">
                    {#if selectable}<th class="w-12 pl-4"><span class="sr-only">Pick</span></th>{/if}
                    {#each group.headers as header (header.id)}
                        {@const meta = header.column.columnDef.meta}
                        {@const sorted = header.column.getIsSorted()}
                        <th
                            aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : undefined}
                            class={[
                                "h-10 px-2 font-mono text-2xs font-normal tracking-wider whitespace-nowrap text-gray-400 uppercase first:pl-4 last:pr-4",
                                aligned(meta?.align),
                                meta?.class,
                            ]}
                        >
                            {#if header.column.getCanSort()}
                                <button
                                    type="button"
                                    class={[
                                        "inline-flex items-center gap-1 rounded-md uppercase hover:text-gray-100 focus-visible:outline-2 focus-visible:outline-accent",
                                        sorted && "text-gray-100",
                                        meta?.align === "end" && "flex-row-reverse",
                                    ]}
                                    onclick={header.column.getToggleSortingHandler()}
                                >
                                    <FlexRender {header} />
                                    {#if sorted === "asc"}
                                        <MaterialSymbolsArrowUpwardRounded class="size-3" />
                                    {:else if sorted === "desc"}
                                        <MaterialSymbolsArrowDownwardRounded class="size-3" />
                                    {/if}
                                </button>
                            {:else}
                                <FlexRender {header} />
                            {/if}
                        </th>
                    {/each}
                </tr>
            {/each}
        </thead>
        <tbody class="divide-y divide-white/5">
            {#each rows as row (row.id)}
                <tr
                    tabindex={onrowclick ? 0 : undefined}
                    aria-current={active === row.id || undefined}
                    class={[
                        "transition-colors aria-[current]:bg-white/5",
                        onrowclick &&
                            "cursor-pointer hover:bg-white/5 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent",
                    ]}
                    onclick={() => onrowclick?.(row.original)}
                    onkeydown={(event) => {
                        if (onrowclick && (event.key === "Enter" || event.key === " ") && event.target === event.currentTarget) {
                            event.preventDefault();
                            onrowclick(row.original);
                        }
                    }}
                >
                    {#if selectable}
                        <td class="w-12 py-2 pl-4" onclick={(event) => event.stopPropagation()}>
                            <Checkbox label="Pick this row" bind:checked={() => row.getIsSelected(), (on) => row.toggleSelected(on)} />
                        </td>
                    {/if}
                    {#each row.getAllCells() as cell (cell.id)}
                        {@const meta = cell.column.columnDef.meta}
                        <td class={["h-14 px-2 first:pl-4 last:pr-4", aligned(meta?.align), meta?.class]}>
                            <FlexRender {cell} />
                        </td>
                    {/each}
                </tr>
            {/each}
        </tbody>
    </table>
</div>
