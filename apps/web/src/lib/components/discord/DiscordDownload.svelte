<script lang="ts">
    import DiscordTooltip from "#lib/components/discord/DiscordTooltip.svelte";
    import type { ClassValue } from "svelte/elements";
    import MaterialSymbolsDownloadRounded from "~icons/material-symbols/download-rounded";

    let { src, name, class: className }: { src: string; name?: string; class?: ClassValue } = $props();
</script>

<div
    class={[
        "absolute top-1 right-1 z-10 flex items-center rounded-md bg-dc-media-panel transition-opacity duration-200",
        className ??
            "pointer-events-none opacity-0 group-hover/media:pointer-events-auto group-hover/media:opacity-100 focus-within:pointer-events-auto focus-within:opacity-100",
    ]}
>
    <DiscordTooltip content="Download">
        <a
            href={src}
            download={name || ""}
            target="_blank"
            rel="noopener noreferrer"
            class="flex size-8 cursor-pointer items-center justify-center text-dc-media-icon hover:text-white [&_svg]:size-5"
        >
            <MaterialSymbolsDownloadRounded />
        </a>
    </DiscordTooltip>
</div>
