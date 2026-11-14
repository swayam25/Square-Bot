<script lang="ts">
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Cover from "#lib/components/ui/Cover.svelte";
    import Shape from "#lib/components/ui/Shape.svelte";
    import WavyProgress from "#lib/components/ui/WavyProgress.svelte";
    import { time } from "#lib/format.ts";
    import { ripple } from "#lib/motion.ts";
    import * as music from "#lib/music.remote.ts";
    import MaterialSymbolsArrowForwardRounded from "~icons/material-symbols/arrow-forward-rounded";

    let { guild }: { guild: string } = $props();

    const playerQuery = $derived(music.livePlayer(guild));
    const player = $derived(playerQuery.current);
    const track = $derived(player?.track ?? null);
    const playing = $derived(!!track && !player?.paused);

    let now = $state(Date.now());
    $effect(() => {
        if (!playing) return;
        let frame = requestAnimationFrame(function tick() {
            now = Date.now();
            frame = requestAnimationFrame(tick);
        });
        return () => cancelAnimationFrame(frame);
    });

    const position = $derived.by(() => {
        if (!player || !track) return 0;
        const at = player.positionMs + (player.paused ? 0 : Math.max(0, now - player.positionAt));
        return track.isStream ? at : Math.min(at, track.lengthMs);
    });
</script>

<a
    href="/guild/{guild}/player"
    aria-label={track ? `Open the player: ${track.title} by ${track.author}` : "Open the player"}
    class="group ripple relative isolate flex flex-col gap-4 overflow-clip rounded-3xl bg-gray-900 p-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    {@attach ripple}
>
    {#if track?.artworkUrl}
        <img
            src={track.artworkUrl}
            alt=""
            aria-hidden="true"
            referrerpolicy="no-referrer"
            class="absolute inset-0 -z-10 size-full scale-125 object-cover opacity-30 blur-3xl"
        />
        <span aria-hidden="true" class="absolute inset-0 -z-10 bg-linear-to-r from-gray-900 via-gray-900/70 to-gray-900/30"></span>
    {:else}
        <Shape
            lobes={12}
            depth={0.05}
            class="absolute -top-20 -right-16 -z-10 size-64 text-accent/10 transition-transform duration-700 group-hover:rotate-12"
        />
        <Shape lobes={4} depth={0.2} class="absolute right-40 -bottom-10 -z-10 size-20 rotate-12 text-violet-500/30" />
    {/if}

    <div class="flex items-center gap-4">
        <span class="relative shrink-0">
            <Cover src={track?.artworkUrl} class="size-20 rounded-2xl text-accent shadow-xl shadow-black/40 md:size-24" />
        </span>

        <span class="flex min-w-0 flex-1 flex-col gap-1">
            <span class="font-mono text-2xs font-semibold tracking-wider text-accent uppercase">
                {track ? (player?.paused ? "Paused" : "Now playing") : "Player"}
            </span>
            {#if track}
                <span class="truncate font-display text-xl font-semibold md:text-2xl">{track.title}</span>
                <span class="flex min-w-0 items-center gap-2 text-sm text-gray-400">
                    <span class="truncate">{track.author}</span>
                    {#if track.requester}
                        <span aria-hidden="true">·</span>
                        <span class="flex max-w-[50%] shrink-0 items-center gap-2">
                            <Avatar src={track.requester.avatarUrl} name={track.requester.name} class="size-5 text-2xs" />
                            <span class="truncate">{track.requester.name}</span>
                        </span>
                    {/if}
                </span>
            {:else if player}
                <span class="font-display text-xl font-semibold">Nothing is playing</span>
                <span class="text-sm text-gray-400">Open the player to search and queue something.</span>
            {:else}
                <span aria-hidden="true" class="h-7 w-48 skeleton rounded-full"></span>
                <span aria-hidden="true" class="h-5 w-32 skeleton rounded-full"></span>
            {/if}
        </span>

        <span
            class="hidden shrink-0 items-center gap-2 rounded-full bg-gray-800 px-4 text-sm font-medium transition-colors group-hover:bg-gray-700 sm:flex sm:h-10"
        >
            Open player<MaterialSymbolsArrowForwardRounded class="size-4" />
        </span>
    </div>

    {#if track}
        <div class="flex items-center gap-4 font-mono text-xs text-gray-400">
            <span class="w-12 shrink-0">{time(position)}</span>
            <WavyProgress
                value={track.isStream ? 1 : track.lengthMs ? position / track.lengthMs : 0}
                live={track.isStream}
                {playing}
                label="{time(position)} of {track.isStream ? 'a live stream' : time(track.lengthMs)}"
                class="min-w-0 flex-1"
            />
            <span class="w-12 shrink-0 text-right">{track.isStream ? "Live" : time(track.lengthMs)}</span>
        </div>
    {/if}
</a>
