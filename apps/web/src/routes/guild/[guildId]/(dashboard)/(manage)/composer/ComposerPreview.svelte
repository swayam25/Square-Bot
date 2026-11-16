<script lang="ts">
    import DiscordAccessories from "#lib/components/discord/DiscordAccessories.svelte";
    import DiscordActionRow from "#lib/components/discord/DiscordActionRow.svelte";
    import DiscordButton from "#lib/components/discord/DiscordButton.svelte";
    import DiscordContainer from "#lib/components/discord/DiscordContainer.svelte";
    import DiscordEmoji from "#lib/components/discord/DiscordEmoji.svelte";
    import DiscordFile from "#lib/components/discord/DiscordFile.svelte";
    import DiscordGallery from "#lib/components/discord/DiscordGallery.svelte";
    import DiscordMarkdown from "#lib/components/discord/DiscordMarkdown.svelte";
    import DiscordMessage from "#lib/components/discord/DiscordMessage.svelte";
    import DiscordSpoilerCover from "#lib/components/discord/DiscordSpoilerCover.svelte";
    import DiscordWindow from "#lib/components/discord/DiscordWindow.svelte";
    import { setDiscord } from "#lib/discord/context.ts";
    import type { Channel, Role } from "@square/api-client";
    import { getComposer, isVideo, parseEmoji, validUrl, type Block, type LinkButton, type Media } from "./composer.svelte.ts";

    let {
        blocks,
        name,
        avatar,
        channel,
        channels,
        roles,
    }: { blocks: Block[]; name: string; avatar: string; channel: string; channels: Channel[]; roles: Role[] } = $props();

    const composer = getComposer();

    setDiscord({
        users: {},
        get roles() {
            return Object.fromEntries(roles.map((role) => [role.id, { name: role.name, color: role.color ?? undefined }]));
        },
        get channels() {
            return Object.fromEntries(channels.map((entry) => [entry.id, entry.name]));
        },
        fileUrl: (file) => file.url,
    });

    function fileOf(url: string) {
        const upload = composer.uploads.of(url);
        if (upload) {
            const kind = upload.file.type.startsWith("image/") ? "image" : isVideo(upload.name, upload.file.type) ? "video" : "file";
            return { name: upload.name, url: upload.url, size: upload.file.size, kind } as const;
        }
        if (!validUrl(url)) return null;
        const path = url.trim().split("?")[0] ?? "";
        return { name: path.slice(path.lastIndexOf("/") + 1), url: url.trim(), kind: isVideo(path) ? "video" : "image" } as const;
    }

    const shown = (items: Media[]) =>
        items.flatMap((item) => {
            const file = fileOf(item.url);
            return file ? [{ ...file, spoiler: item.spoiler }] : [];
        });
</script>

{#snippet button(entry: LinkButton)}
    {@const emoji = entry.emoji ? parseEmoji(entry.emoji) : null}
    <DiscordButton href={entry.url.trim() || ""} disabled={entry.disabled}>
        {#if emoji}<DiscordEmoji {...emoji} tooltip={false} />{/if}
        {#if entry.label.trim()}<span>{entry.label}</span>{/if}
    </DiscordButton>
{/snippet}

{#snippet piece(block: Block)}
    {#if block.kind === "container"}
        <DiscordSpoilerCover spoiler={block.spoiler} class="w-full max-w-150 rounded-lg">
            <DiscordContainer color={block.color}>
                {#each block.children as child (child.id)}{@render piece(child)}{/each}
            </DiscordContainer>
        </DiscordSpoilerCover>
    {:else if block.kind === "text"}
        {#if block.text.trim()}<DiscordMarkdown text={block.text} />{/if}
    {:else if block.kind === "section"}
        <div class="flex w-full max-w-150 items-start gap-4">
            <div class="flex min-w-0 flex-1 flex-col gap-2">
                {#each block.texts as entry (entry.id)}
                    {#if entry.text.trim()}<DiscordMarkdown text={entry.text} />{/if}
                {/each}
            </div>
            {#if block.accessory.kind === "button"}
                {@render button(block.accessory)}
            {:else}
                {@const file = fileOf(block.accessory.media.url)}
                {#if file}
                    <DiscordSpoilerCover spoiler={block.accessory.media.spoiler} class="size-21.25 shrink-0 rounded-lg">
                        {#if file.kind === "video"}
                            <video src={file.url} muted preload="metadata" class="size-21.25 shrink-0 rounded-lg object-cover"></video>
                        {:else}
                            <img src={file.url} alt={block.accessory.media.description} class="size-21.25 shrink-0 rounded-lg object-cover" />
                        {/if}
                    </DiscordSpoilerCover>
                {/if}
            {/if}
        </div>
    {:else if block.kind === "gallery"}
        <DiscordGallery files={shown(block.items)} missing="Discord can't load this link" />
    {:else if block.kind === "file"}
        {@const file = fileOf(block.url)}
        {#if file}
            <DiscordSpoilerCover spoiler={block.spoiler} class="w-108 max-w-full rounded-lg">
                <DiscordFile file={{ ...file, kind: "file" }} />
            </DiscordSpoilerCover>
        {/if}
    {:else if block.kind === "separator"}
        <div class={["w-full max-w-150", block.large && "my-2", block.divider && "h-px bg-dc-border"]}></div>
    {:else if block.kind === "row"}
        <DiscordActionRow>
            {#each block.buttons as entry (entry.id)}{@render button(entry)}{/each}
        </DiscordActionRow>
    {/if}
{/snippet}

<DiscordWindow {channel}>
    <DiscordMessage {name} {avatar}>
        {#if blocks.length}
            <DiscordAccessories>
                {#each blocks as block (block.id)}{@render piece(block)}{/each}
            </DiscordAccessories>
        {:else}
            <p class="text-dc-muted italic">Add a component to see it here.</p>
        {/if}
    </DiscordMessage>
</DiscordWindow>
