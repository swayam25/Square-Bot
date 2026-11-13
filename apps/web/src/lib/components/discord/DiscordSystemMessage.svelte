<script lang="ts">
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import type { Snippet } from "svelte";
    import type { ClassValue } from "svelte/elements";

    let {
        id,
        kind = "other",
        time,
        timeTitle,
        class: className,
        children,
    }: {
        id?: string;
        kind?: "join" | "pin" | "boost" | "other";
        time: string;
        timeTitle?: string;
        class?: ClassValue;
        children: Snippet;
    } = $props();

    const icons = {
        join: "M4 12h15m-6-6 6 6-6 6",
        other: "M4 12h15m-6-6 6 6-6 6",
        pin: "M9 3h6m-5 0v6l-3 5h10l-3-5V3m-2 11v7",
        boost: "m12 3 7 9-7 9-7-9z",
    };
</script>

<div {id} class={["relative min-h-5.5 py-0.5 pr-4 pl-18 wrap-anywhere text-dc-muted hover:bg-dc-hover", className]}>
    <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        class={[
            "absolute top-1.25 left-7 size-4 fill-none stroke-current stroke-2 [stroke-linecap:round] [stroke-linejoin:round]",
            kind === "join" && "text-[#23a55a]",
            kind === "boost" && "text-[#ff73fa]",
        ]}
    >
        <path d={icons[kind]} />
    </svg>
    {@render children()}
    <Tooltip lazy content={timeTitle} class="ml-1"><time class="text-xs font-medium">{time}</time></Tooltip>
</div>
