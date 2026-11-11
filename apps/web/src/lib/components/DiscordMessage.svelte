<script lang="ts">
    import swayam from "#lib/assets/discord/swayam.webp";
    import square from "#lib/assets/square.svg";
    import type { Snippet } from "svelte";
    import MaterialSymbolsPlayShapesRounded from "~icons/material-symbols/play-shapes-rounded";
    import MaterialSymbolsVisibilityRounded from "~icons/material-symbols/visibility-rounded";

    let { command, ephemeral = false, children }: { command?: string; ephemeral?: boolean; children: Snippet } = $props();
</script>

<div class={["relative py-0.5 pr-4 pl-18 wrap-anywhere", ephemeral && "bg-[#5865f2]/5 shadow-[inset_2px_0_#5865f2]"]}>
    {#if command}
        <div class="relative mb-1 flex h-4.5 items-center gap-1 text-sm leading-4.5 whitespace-nowrap text-[#efeff1]">
            <span aria-hidden="true" class="absolute top-1.75 -left-9 h-3.5 w-8 rounded-tl-md border-t-2 border-l-2 border-[#474851]"></span>
            <img src={swayam} alt="" class="size-4 rounded-full" />
            <span class="mr-1 font-medium text-[#ababaf]">Swayam</span>
            used
            <span class="flex items-center gap-1 rounded bg-[#5865f2]/24 px-0.5 text-xs text-[#4d96ee]">
                <MaterialSymbolsPlayShapesRounded class="size-3.5" />
                {command}
            </span>
        </div>
    {/if}
    <div class="relative leading-5.5">
        <span class="absolute top-0 -left-14 flex size-10 items-center justify-center rounded-full bg-mist-950">
            <img src={square} alt="" class="size-7" />
        </span>
        <span class="font-medium text-[#fbfbfb]">Square</span>
        <span class="relative -top-px ml-1 inline-block rounded bg-[#5865f2] px-1 align-middle text-[10px] leading-3.75 font-semibold text-white"
            >APP</span
        >
        <span class="ml-1 text-xs font-medium text-[#81828a]">9:04 PM</span>
    </div>
    <div class="grid justify-items-start gap-1 py-0.5">{@render children()}</div>
    {#if ephemeral}
        <div class="mt-1 flex items-center gap-1 text-xs text-[#8b8d94]">
            <MaterialSymbolsVisibilityRounded class="size-4" />
            Only you can see this •<span class="text-[#4d96ee]">Dismiss message</span>
        </div>
    {/if}
</div>
