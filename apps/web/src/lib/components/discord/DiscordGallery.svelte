<script lang="ts">
    import { getDiscord } from "#lib/discord/context.ts";
    import type { TranscriptFile } from "@square/api-client";
    import MaterialSymbolsImageNotSupportedRounded from "~icons/material-symbols/image-not-supported-rounded";

    let { files }: { files: TranscriptFile[] } = $props();

    const discord = getDiscord();
    const count = $derived(files.length);
    let broken = $state<Record<number, boolean>>({});

    // Discord's mosaic: 2 to 4 have their own layouts, more fill rows of three with the leftover one or two on top
    function span(index: number) {
        if (count === 2 || count === 4) return "col-span-3 aspect-square";
        if (count === 3) return index === 0 ? "row-span-2" : "aspect-square";
        const leftover = count % 3;
        if (index >= leftover) return "col-span-2 aspect-square";
        return leftover === 1 ? "col-span-6 aspect-video" : "col-span-3 aspect-square";
    }
</script>

{#snippet media(file: TranscriptFile, index: number, tile: boolean)}
    {@const src = discord.fileUrl(file)}
    {@const shape = tile ? ["size-full rounded-xs object-cover", span(index)] : "max-h-87.5 w-auto max-w-full rounded-lg object-contain"}
    {#if !src || broken[index]}
        <div
            class={[
                "flex min-h-24 min-w-50 flex-col items-center justify-center gap-1 bg-dc-surface p-4 text-center text-xs text-dc-muted",
                tile ? ["rounded-xs", span(index)] : "rounded-lg border border-dc-border",
            ]}
        >
            <MaterialSymbolsImageNotSupportedRounded class="size-6" />
            <span class="max-w-full truncate">{file.name || "Picture"}</span>
            <span>No longer on Discord</span>
        </div>
    {:else if file.kind === "video"}
        <!-- svelte-ignore a11y_media_has_caption -->
        <video {src} controls preload="metadata" width={file.width} height={file.height} class={[shape, "bg-black"]}></video>
    {:else if discord.view}
        <button
            type="button"
            class={["cursor-pointer overflow-hidden", tile ? span(index) : "max-w-full rounded-lg"]}
            onclick={() => discord.view?.(src)}
        >
            <img
                {src}
                alt={file.name || "View full size"}
                width={file.width}
                height={file.height}
                loading="lazy"
                data-discord-image
                class={[tile ? "size-full rounded-xs object-cover" : "max-h-87.5 w-auto max-w-full rounded-lg object-contain", "bg-dc-surface"]}
                onerror={() => (broken[index] = true)}
            />
        </button>
    {:else}
        <img
            {src}
            alt={file.name || "View full size"}
            width={file.width}
            height={file.height}
            loading="lazy"
            class={[shape, "bg-dc-surface"]}
            onerror={() => (broken[index] = true)}
        />
    {/if}
{/snippet}

{#if count === 1}
    <div class="max-w-[min(550px,100%)]">{@render media(files[0], 0, false)}</div>
{:else if count}
    <div class={["grid w-137.5 max-w-full gap-1 overflow-hidden rounded-lg", count === 3 ? "grid-cols-[2fr_1fr]" : "grid-cols-6"]}>
        {#each files as file, index (index)}
            {@render media(file, index, true)}
        {/each}
    </div>
{/if}
