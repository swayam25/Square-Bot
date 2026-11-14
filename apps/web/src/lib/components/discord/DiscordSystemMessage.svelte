<script lang="ts">
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import type { Snippet } from "svelte";
    import type { ClassValue } from "svelte/elements";
    import MaterialSymbolsArrowForwardRounded from "~icons/material-symbols/arrow-forward-rounded";
    import MaterialSymbolsKeepRounded from "~icons/material-symbols/keep-rounded";
    import MaterialSymbolsRocketLaunchRounded from "~icons/material-symbols/rocket-launch-rounded";

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
        join: MaterialSymbolsArrowForwardRounded,
        other: MaterialSymbolsArrowForwardRounded,
        pin: MaterialSymbolsKeepRounded,
        boost: MaterialSymbolsRocketLaunchRounded,
    };
    const Icon = $derived(icons[kind]);
</script>

<div {id} class={["relative min-h-5.5 py-0.5 pr-4 pl-18 wrap-anywhere text-dc-muted hover:bg-dc-hover", className]}>
    <Icon aria-hidden="true" class={["absolute top-1.25 left-7 size-4", kind === "join" && "text-dc-online", kind === "boost" && "text-dc-boost"]} />
    {@render children()}
    <Tooltip lazy content={timeTitle} class="ml-1"><time class="text-xs font-medium">{time}</time></Tooltip>
</div>
