<script module lang="ts">
    import type { JoinDay } from "@square/api-client";
    import { BarChart } from "layerchart";
    import type { ComponentProps } from "svelte";

    const shortDate = (date: string) =>
        new Date(`${date}T00:00:00Z`).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });

    const series = [{ key: "count", label: "Joined", color: "var(--color-accent)" }];
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

<script lang="ts">
    let { days }: { days: JoinDay[] } = $props();

    const yDomain = $derived([0, Math.max(4, ...days.map((day) => day.count))]);
</script>

<BarChart data={days} x="date" y="count" {yDomain} {series} props={chartProps} />
