<script lang="ts">
    import { livePlayer, liveQueue, liveStatus } from "#lib/music.remote.ts";
    import type { PageProps } from "./$types";

    let { params }: PageProps = $props();

    const player = $derived(livePlayer(params.guildId));
    const queue = $derived(liveQueue(params.guildId));
    const status = liveStatus();

    let now = $state(Date.now());
    $effect(() => {
        const timer = setInterval(() => (now = Date.now()), 1000);
        return () => clearInterval(timer);
    });

    // The clock only runs on its own while the bot is there to say it's still playing
    function position(state: Awaited<typeof player>, online: boolean) {
        const elapsed = state.paused || !online ? 0 : now - state.positionAt;
        return Math.min(state.positionMs + elapsed, state.track?.lengthMs ?? 0);
    }

    const time = (ms: number) => `${Math.floor(ms / 60_000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")}`;
</script>

<!-- NOTE: placeholder to exercise live updates. The music panel UI comes with the design system. -->
<p><a href="/">Back</a> · {(await status) ? "Square is online" : "Square is offline, showing the last known state"}</p>

{#await player then state}
    {#if state.track}
        <p>
            {state.paused ? "Paused" : "Playing"}: {state.track.title} by {state.track.author}
            ({state.track.isStream ? "live" : `${time(position(state, await status))} / ${time(state.track.lengthMs)}`})
        </p>
        <p>Volume {state.volume} · loop {state.loop} · shuffle {state.shuffle ? "on" : "off"}</p>
    {:else}
        <p>Nothing playing</p>
    {/if}
{:catch err}
    <p>{err.message}</p>
{/await}

{#await queue then state}
    <p>Up next ({state.total})</p>
    <ol>
        {#each state.tracks as track, i (i)}
            <li>{track.title} by {track.author}</li>
        {/each}
    </ol>
{/await}
