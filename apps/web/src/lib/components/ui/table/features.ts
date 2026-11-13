import {
    createSortedRowModel,
    rowSelectionFeature,
    rowSortingFeature,
    sortFn_basic,
    tableFeatures,
    type ColumnDef,
    type RowData,
} from "@tanstack/svelte-table";

export type TableColumnMeta = {
    align?: "start" | "end";
    class?: string;
};

export const features = tableFeatures({
    rowSortingFeature,
    sortedRowModel: createSortedRowModel(),
    sortFns: { basic: sortFn_basic },
    rowSelectionFeature,
    columnMeta: {} as TableColumnMeta,
});

export type Features = typeof features;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type TableColumn<T extends RowData> = ColumnDef<Features, T, any>;
