<script module lang="ts">
    import { BarChart } from "layerchart";
    import type { ComponentProps } from "svelte";

    export type Series<T> = { key: keyof T & string; label: string; color: string }[];

    const shortDate = (date: string) =>
        new Date(`${date}T00:00:00Z`).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });

    // Kept at module scope: LayerChart re-nests spread props, and a new object per render once looped the page
    const chartProps: ComponentProps<typeof BarChart>["props"] = {
        bars: { radius: 4, rounded: "top" },
        xAxis: {
            format: shortDate,
            ticks: (scale: { domain: () => string[] }) => {
                const days = scale.domain();
                return days.filter((_, index) => (days.length - 1 - index) % 7 === 0);
            },
        },
        yAxis: { ticks: (scale: { ticks?: (count: number) => number[] }) => scale.ticks?.(4).filter(Number.isInteger) },
        tooltip: { header: { format: shortDate } },
    };
</script>

<script lang="ts" generics="T extends { date: string }">
    // `series` should be a constant, for the same reason as `chartProps`
    let { days, series }: { days: T[]; series: Series<T> } = $props();

    const yDomain = $derived([0, Math.max(4, ...days.flatMap((day) => series.map(({ key }) => Number(day[key]))))]);
</script>

<BarChart data={days} x="date" {series} seriesLayout={series.length > 1 ? "group" : undefined} {yDomain} props={chartProps} />
