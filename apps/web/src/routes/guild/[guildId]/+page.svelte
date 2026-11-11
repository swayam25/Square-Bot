<script lang="ts">
    import PageHeading from "#lib/components/PageHeading.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import * as music from "#lib/music.remote.ts";
    import MaterialSymbolsArrowForwardRounded from "~icons/material-symbols/arrow-forward-rounded";
    import MaterialSymbolsMusicNoteRounded from "~icons/material-symbols/music-note-rounded";
    import MaterialSymbolsPauseRounded from "~icons/material-symbols/pause-rounded";
    import MaterialSymbolsPlayArrowRounded from "~icons/material-symbols/play-arrow-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    const player = $derived(await music.livePlayer(data.guild.id));
</script>

<div class="flex flex-col gap-8">
    <PageHeading title="Overview" description="What's happening in {data.guild.name} right now." />

    <section aria-labelledby="now-playing" class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
        <div class="flex items-center justify-between gap-4">
            <h2 id="now-playing" class="font-display text-xl font-semibold">Now playing</h2>
            <Button href="/guild/{data.guild.id}/music">Open player<MaterialSymbolsArrowForwardRounded /></Button>
        </div>
        {#if player.track}
            <div class="flex items-center gap-4">
                {#if player.track.artworkUrl}
                    <img src={player.track.artworkUrl} alt="" class="size-16 shrink-0 rounded-2xl object-cover" />
                {:else}
                    <div class="flex size-16 shrink-0 items-center justify-center rounded-2xl bg-surface-2">
                        <MaterialSymbolsMusicNoteRounded class="size-8 text-accent" />
                    </div>
                {/if}
                <div class="flex min-w-0 flex-1 flex-col">
                    <p class="truncate font-semibold">{player.track.title}</p>
                    <p class="truncate text-sm text-mist-400">{player.track.author}</p>
                </div>
                {#if player.paused}
                    <Chip tone="warning"><MaterialSymbolsPlayArrowRounded />Paused</Chip>
                {:else}
                    <Chip tone="accent"><MaterialSymbolsPauseRounded />Playing</Chip>
                {/if}
            </div>
        {:else}
            <p class="text-mist-400">Nothing is playing. Start something with /play in Discord or from the player.</p>
        {/if}
    </section>
</div>
