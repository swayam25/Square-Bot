<script lang="ts">
    import DiscordMarkdown from "#lib/components/discord/DiscordMarkdown.svelte";
    import { getDiscord } from "#lib/discord/context.ts";
    import { calendar } from "#lib/discord/markdown.ts";
    import type { TranscriptEmbed } from "@square/api-client";

    let { embed }: { embed: TranscriptEmbed } = $props();

    const discord = getDiscord();
    const safe = (url: string | undefined) => (url && URL.canParse(url) && /^https?:$/.test(new URL(url).protocol) ? url : undefined);
</script>

{#snippet picture(src: string, className: string)}
    {#if discord.view}
        <button type="button" class={["cursor-pointer", className]} onclick={() => discord.view?.(src)}>
            <img {src} alt="View full size" loading="lazy" data-discord-image class="size-full rounded-sm object-cover" />
        </button>
    {:else}
        <img {src} alt="" loading="lazy" class={["rounded-sm object-cover", className]} />
    {/if}
{/snippet}

{#if embed.media === "video" && embed.mediaUrl}
    <video src={embed.mediaUrl} autoplay loop muted playsinline class="max-h-87.5 max-w-[min(550px,100%)] rounded-lg bg-black"></video>
{:else if embed.media === "image" && embed.mediaUrl}
    {@render picture(embed.mediaUrl, "max-h-87.5 max-w-[min(550px,100%)]")}
{:else}
    <div
        style:border-left-color={embed.color || "var(--color-dc-embed)"}
        class="grid max-w-129 grid-cols-[minmax(0,1fr)_auto] rounded-sm border border-l-4 border-dc-border bg-dc-surface pt-2 pr-4 pb-4 pl-3 text-sm leading-4.5"
    >
        <div class="flex min-w-0 flex-col gap-2 pt-2">
            {#if embed.author}
                <div class="flex items-center gap-2 font-semibold text-dc-strong">
                    {#if embed.authorIcon}<img src={embed.authorIcon} alt="" loading="lazy" class="size-6 rounded-full" />{/if}
                    <span class="min-w-0 wrap-anywhere">{embed.author}</span>
                </div>
            {/if}
            {#if embed.title}
                <div class="text-base leading-5.5 font-semibold wrap-anywhere text-dc-strong">
                    {#if safe(embed.url)}
                        <a href={safe(embed.url)} target="_blank" rel="noopener noreferrer" class="text-dc-link hover:underline">{embed.title}</a>
                    {:else}
                        {embed.title}
                    {/if}
                </div>
            {/if}
            {#if embed.description}<DiscordMarkdown text={embed.description} />{/if}
            {#if embed.fields?.length}
                <div class="grid grid-cols-12 gap-2">
                    {#each embed.fields as field, index (index)}
                        <div class={field.inline ? "col-span-12 sm:col-span-4" : "col-span-12"}>
                            <div class="mb-0.5 font-semibold wrap-anywhere text-dc-strong">{field.name}</div>
                            <DiscordMarkdown text={field.value} />
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
        {#if embed.thumbnail}
            {@render picture(embed.thumbnail, "mt-2 ml-4 size-20")}
        {/if}
        {#if embed.image}
            {@render picture(embed.image, "col-span-2 mt-4 max-h-75 max-w-full justify-self-start")}
        {/if}
        {#if embed.footer || embed.time}
            <div class="col-span-2 mt-2 flex items-center gap-2 text-xs leading-4 font-medium text-dc-muted">
                {#if embed.footerIcon}<img src={embed.footerIcon} alt="" loading="lazy" class="size-5 rounded-full" />{/if}
                <span class="min-w-0 wrap-anywhere">
                    {embed.footer ?? ""}{embed.footer && embed.time ? " • " : ""}{embed.time ? calendar(embed.time) : ""}
                </span>
            </div>
        {/if}
    </div>
{/if}
