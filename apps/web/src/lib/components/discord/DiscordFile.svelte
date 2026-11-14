<script lang="ts">
    import DiscordTooltip from "#lib/components/discord/DiscordTooltip.svelte";
    import { getDiscord } from "#lib/discord/context.ts";
    import { fileSize } from "#lib/discord/markdown.ts";
    import type { TranscriptFile } from "@square/api-client";
    import MaterialSymbolsDownloadRounded from "~icons/material-symbols/download-rounded";

    let { file }: { file: TranscriptFile } = $props();

    const discord = getDiscord();
    const href = $derived(discord.fileUrl(file));
    const playable = $derived(href && file.kind === "audio");
</script>

<div class="flex w-108 max-w-full flex-col gap-3 rounded-lg border border-dc-border bg-dc-surface p-4">
    <div class="flex items-center gap-2">
        <svg viewBox="0 0 30 40" aria-hidden="true" class="h-10 w-7.5 shrink-0">
            <path class="fill-dc-file" d="M0 3a3 3 0 0 1 3-3h17l10 10v27a3 3 0 0 1-3 3H3a3 3 0 0 1-3-3z" />
            <path class="fill-dc-file-fold" d="M20 0l10 10h-7a3 3 0 0 1-3-3z" />
        </svg>
        <div class="flex min-w-0 flex-1 flex-col">
            {#if href}
                <a {href} target="_blank" rel="noopener noreferrer" class="truncate leading-5 text-dc-link hover:underline">{file.name}</a>
            {:else}
                <span class="truncate leading-5 text-dc-text">{file.name}</span>
            {/if}
            <span class="text-xs leading-4 text-dc-muted">
                {file.size ? fileSize(file.size) : ""}{file.size && !href ? " · " : ""}{href ? "" : "No longer on Discord"}
            </span>
        </div>
        {#if href}
            <DiscordTooltip content="Download"
                ><a {href} target="_blank" rel="noopener noreferrer" class="text-dc-icon hover:text-dc-strong">
                    <MaterialSymbolsDownloadRounded aria-hidden="true" class="size-6" />
                    <span class="sr-only">Download {file.name}</span>
                </a></DiscordTooltip
            >
        {/if}
    </div>
    {#if playable}
        <audio src={href} controls preload="none" class="h-9 w-full"></audio>
    {/if}
</div>
