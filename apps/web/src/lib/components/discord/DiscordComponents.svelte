<script lang="ts">
    import DiscordActionRow from "#lib/components/discord/DiscordActionRow.svelte";
    import DiscordButton from "#lib/components/discord/DiscordButton.svelte";
    import DiscordContainer from "#lib/components/discord/DiscordContainer.svelte";
    import DiscordDownload from "#lib/components/discord/DiscordDownload.svelte";
    import DiscordEmoji from "#lib/components/discord/DiscordEmoji.svelte";
    import DiscordFile from "#lib/components/discord/DiscordFile.svelte";
    import DiscordGallery from "#lib/components/discord/DiscordGallery.svelte";
    import DiscordMarkdown from "#lib/components/discord/DiscordMarkdown.svelte";
    import DiscordSelect from "#lib/components/discord/DiscordSelect.svelte";
    import { getDiscord, getMessageAuthor } from "#lib/discord/context.ts";
    import type { TranscriptComponent } from "@square/api-client";

    let { components }: { components: TranscriptComponent[] } = $props();

    const discord = getDiscord();
    const author = getMessageAuthor();
</script>

{#snippet piece(component: TranscriptComponent)}
    {#if component.kind === "container"}
        <DiscordContainer color={component.color}>
            {#each component.children ?? [] as child, index (index)}{@render piece(child)}{/each}
        </DiscordContainer>
    {:else if component.kind === "text"}
        <DiscordMarkdown text={component.text ?? ""} />
    {:else if component.kind === "section"}
        <div class="flex items-start gap-4">
            <div class="flex min-w-0 flex-1 flex-col gap-2">
                {#each component.children ?? [] as child, index (index)}{@render piece(child)}{/each}
            </div>
            {#if component.accessory}{@render piece(component.accessory)}{/if}
        </div>
    {:else if component.kind === "thumbnail"}
        {@const src = component.files?.[0] ? discord.fileUrl(component.files[0]) : null}
        {#if src}
            <div class="group/media relative size-21.25 shrink-0">
                {#if discord.view}
                    <button
                        type="button"
                        class="block size-full cursor-pointer"
                        onclick={() => discord.view?.({ media: [{ src, kind: "image" }], index: 0, author })}
                    >
                        <img {src} alt="View full size" loading="lazy" class="size-full rounded-lg object-cover" />
                    </button>
                {:else}
                    <img {src} alt="" loading="lazy" class="size-full rounded-lg object-cover" />
                {/if}
                <DiscordDownload {src} name={component.files?.[0]?.name} />
            </div>
        {/if}
    {:else if component.kind === "gallery"}
        <DiscordGallery files={component.files ?? []} />
    {:else if component.kind === "file"}
        {#if component.files?.[0]}<DiscordFile file={component.files[0]} />{/if}
    {:else if component.kind === "separator"}
        <div class={[component.large && "my-2", component.divider && "h-px bg-dc-border"]}></div>
    {:else if component.kind === "row"}
        <DiscordActionRow>
            {#each component.children ?? [] as child, index (index)}{@render piece(child)}{/each}
        </DiscordActionRow>
    {:else if component.kind === "button"}
        <DiscordButton style={component.style || "secondary"} href={component.url || undefined} disabled={component.disabled}>
            {#if component.emoji}<DiscordEmoji {...component.emoji} class="size-4.5" />{/if}
            {#if component.label}<span>{component.label}</span>{/if}
        </DiscordButton>
    {:else if component.kind === "select"}
        <DiscordSelect label={component.label ?? ""} placeholder={component.placeholder} disabled={component.disabled} />
    {/if}
{/snippet}

{#each components as component, index (index)}{@render piece(component)}{/each}
