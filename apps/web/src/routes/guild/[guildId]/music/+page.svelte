<script lang="ts">
    import PageHeading from "#lib/components/PageHeading.svelte";
    import * as music from "#lib/music.remote.ts";
    import type { PageProps } from "./$types";

    let { params }: PageProps = $props();

    const guild = $derived(params.guildId);
    const player = $derived(music.livePlayer(guild));
    const queue = $derived(music.liveQueue(guild));
    const history = $derived(music.liveHistory(guild));
    const presets = $derived(music.eqPresets(guild));
    const status = music.liveStatus();

    // Read with `await` rather than `{#await}` blocks, which rebuild everything inside them on every live value
    const playerState = $derived(await player);
    const queueState = $derived(await queue);
    const played = $derived(await history);

    let search = $state("");
    let results = $state<Awaited<ReturnType<typeof music.searchMusic>> | null>(null);
    async function find() {
        try {
            results = search.trim() ? await music.searchMusic({ guild, query: search.trim() }) : null;
        } catch (err) {
            message = `Search failed: ${(err as { body?: { message?: string } }).body?.message ?? String(err)}`;
        }
    }
    const online = $derived(await status);

    let now = $state(Date.now());
    $effect(() => {
        const timer = setInterval(() => (now = Date.now()), 1000);
        return () => clearInterval(timer);
    });

    function position(state: Awaited<typeof player>, online: boolean) {
        const elapsed = state.paused || !online ? 0 : now - state.positionAt;
        return Math.min(state.positionMs + elapsed, state.track?.lengthMs ?? 0);
    }

    const time = (ms: number) => `${Math.floor(ms / 60_000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")}`;

    let message = $state("");
    async function run(action: Promise<string>) {
        try {
            message = await action;
        } catch (err) {
            message = `Refused: ${(err as { body?: { message?: string } }).body?.message ?? String(err)}`;
        }
    }
</script>

<!-- NOTE: placeholder to exercise live updates and controls. The music panel UI comes with the design system. -->
<PageHeading title="Music" description="The player, queue and history." />
<p>{online ? "Square is online" : "Square is offline, showing the last known state"}</p>
<p>{message}</p>

<form
    onsubmit={(event) => {
        event.preventDefault();
        void find();
    }}
>
    <input bind:value={search} placeholder="Search, or paste a link" />
    <button>Search</button>
    <button type="button" disabled={!search.trim()} onclick={() => run(music.playQuery({ guild, query: search.trim() }))}>Play top result</button>
</form>
{#if results}
    {#if results.playlist}
        <p>
            Playlist {results.playlist.name} ({results.playlist.trackCount} tracks)
            <button onclick={() => run(music.playQuery({ guild, query: search.trim() }))}>Queue playlist</button>
        </p>
    {/if}
    <ul>
        {#each results.tracks as track (track.identifier)}
            <li>
                {track.title} by {track.author}
                <button disabled={!track.uri} onclick={() => run(music.playQuery({ guild, query: track.uri! }))}>Play</button>
            </li>
        {:else}
            <li>No results</li>
        {/each}
    </ul>
{/if}

{#if playerState.track}
    {@const state = playerState}
    {@const track = playerState.track}
    <p>
        {state.paused ? "Paused" : "Playing"}: {track.title} by {track.author}
        ({track.isStream ? "live" : `${time(position(state, online))} / ${time(track.lengthMs)}`})
    </p>
    <p>Volume {state.volume} · loop {state.loop} · shuffle {state.shuffle ? "on" : "off"} · autoplay {state.autoplay ? "on" : "off"}</p>
    <p>
        <button onclick={() => run(music.previousTrack({ guild }))}>Previous</button>
        <button onclick={() => run(music.seekTrack({ guild, positionMs: Math.max(0, position(state, true) - 10_000) }))}>-10s</button>
        <button onclick={() => run(music.setPaused({ guild, paused: !state.paused }))}>{state.paused ? "Resume" : "Pause"}</button>
        <button onclick={() => run(music.seekTrack({ guild, positionMs: position(state, true) + 10_000 }))}>+10s</button>
        <button onclick={() => run(music.skipTrack({ guild }))}>Skip</button>
        <button onclick={() => run(music.stopPlayer({ guild }))}>Stop</button>
    </p>
    <p>
        <label>
            Volume
            <input
                type="range"
                min="1"
                max="100"
                value={state.volume}
                onchange={(e) => run(music.setVolume({ guild, volume: Number(e.currentTarget.value) }))}
            />
        </label>
        <select value={state.loop} onchange={(e) => run(music.setLoop({ guild, mode: e.currentTarget.value as "off" | "track" | "queue" }))}>
            <option value="off">Loop off</option>
            <option value="track">Loop track</option>
            <option value="queue">Loop queue</option>
        </select>
        <button onclick={() => run(music.setShuffle({ guild, enabled: !state.shuffle }))}>Shuffle: {state.shuffle ? "on" : "off"}</button>
        <button onclick={() => run(music.setAutoplay({ guild, enabled: !state.autoplay }))}>Autoplay: {state.autoplay ? "on" : "off"}</button>
    </p>
    <p>
        EQ:
        {#each await presets as preset (preset.name)}
            <button onclick={() => run(music.setEq({ guild, preset: preset.name, enabled: !state.eq.includes(preset.name) }))}>
                {state.eq.includes(preset.name) ? "✓ " : ""}{preset.label}
            </button>
        {/each}
        <button onclick={() => run(music.resetEq({ guild }))}>Reset</button>
    </p>
{:else}
    <p>Nothing playing</p>
{/if}

{#if queueState}
    {@const state = queueState}
    <p>
        Up next ({state.total})
        <button onclick={() => run(music.clearQueue({ guild }))}>Clear</button>
        <button onclick={() => run(music.reverseQueue({ guild }))}>Reverse</button>
        <button onclick={() => run(music.sortQueue({ guild }))}>Sort</button>
        <button onclick={() => run(music.dedupeQueue({ guild }))}>Dedupe</button>
    </p>
    <ol>
        {#each state.tracks as track, index (index)}
            {@const at = { guild, index, identifier: track.identifier }}
            <li>
                {track.title} by {track.author}
                <button onclick={() => run(music.jumpToTrack(at))}>Play now</button>
                <button disabled={index === 0} onclick={() => run(music.moveTrack({ ...at, to: index - 1 }))}>Up</button>
                <button disabled={index === state.tracks.length - 1} onclick={() => run(music.moveTrack({ ...at, to: index + 1 }))}>Down</button>
                <button onclick={() => run(music.removeTrack(at))}>Remove</button>
                {#if track.requesterId}
                    <button onclick={() => run(music.removeRequesterTracks({ guild, userId: track.requesterId! }))}>Remove all by requester</button>
                {/if}
            </li>
        {/each}
    </ol>
{/if}

<p>History ({played.length})</p>
<ol>
    {#each played as track, index (index)}
        <li>
            {track.title} by {track.author}
            <button onclick={() => run(music.replayTrack({ guild, index, identifier: track.identifier }))}>Queue again</button>
        </li>
    {/each}
</ol>
