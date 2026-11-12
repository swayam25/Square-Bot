<script lang="ts">
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Cover from "#lib/components/ui/Cover.svelte";
    import Dialog from "#lib/components/ui/Dialog.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import ScrollRow from "#lib/components/ui/ScrollRow.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { ripple } from "#lib/motion.ts";
    import * as music from "#lib/music.remote.ts";
    import { sortable } from "#lib/sortable.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import type { Person, QueueState, Track } from "@square/api-client";
    import { flushSync } from "svelte";
    import { cubicOut } from "svelte/easing";
    import { SvelteSet } from "svelte/reactivity";
    import { fade } from "svelte/transition";
    import MaterialSymbolsAutoplayRounded from "~icons/material-symbols/autoplay-rounded";
    import MaterialSymbolsClearAllRounded from "~icons/material-symbols/clear-all-rounded";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";
    import MaterialSymbolsDragIndicator from "~icons/material-symbols/drag-indicator";
    import MaterialSymbolsPersonRemoveRounded from "~icons/material-symbols/person-remove-rounded";
    import MaterialSymbolsPlayArrowRounded from "~icons/material-symbols/play-arrow-rounded";
    import MaterialSymbolsSearchRounded from "~icons/material-symbols/search-rounded";
    import MaterialSymbolsSwapVertRounded from "~icons/material-symbols/swap-vert-rounded";
    import SvgSpinners90RingWithBg from "~icons/svg-spinners/90-ring-with-bg";
    import { control, time } from "./player.ts";
    import TrackRow from "./TrackRow.svelte";

    let { guild, queue, autoplay }: { guild: string; queue: QueueState; autoplay: boolean } = $props();

    // A drop shows the new order right away; the bot's next push replaces it either way
    let tracks = $derived<Track[]>(queue.tracks);

    // The drop already shows where rows land, so its reorder must not animate again (see `sortable`)
    let dropping = $state(false);
    async function reorder(from: number, to: number) {
        const moved = tracks[from];
        if (!moved) return;
        const next = [...tracks];
        next.splice(from, 1);
        next.splice(to, 0, moved);
        dropping = true;
        flushSync(() => (tracks = next));
        dropping = false;
        if (!(await control(music.moveTrack({ guild, index: from, identifier: moved.identifier, to })))) tracks = queue.tracks;
    }

    // Rows keep their key when they move, so adds, removals and drops animate instead of rebuilding the list.
    // The same song can be queued twice, hence which copy it is
    function keysOf(list: Track[]) {
        const seen: Record<string, number> = {};
        return list.map((track) => `${track.identifier}:${(seen[track.identifier] = (seen[track.identifier] ?? -1) + 1)}`);
    }
    const keys = $derived(keysOf(tracks));
    const autoKeys = $derived(keysOf(queue.autoplay));

    // Rows only open and close their height, so a reorder from elsewhere (reverse, shuffle, sort, a move in Discord)
    // fades the list into its new order rather than jumping. Only songs in both versions are compared, since a
    // reverse also changes which songs make the first page. A drop here has already landed
    let lastKeys: string[] = [];
    let generation = 0;
    const order = $derived.by(() => {
        const before = new Map(lastKeys.map((key, i) => [key, i]));
        const kept = keys.filter((key) => before.has(key)).map((key) => before.get(key)!);
        const breaks = kept.filter((at, i) => i > 0 && at < kept[i - 1]).length;
        if (breaks && !dropping) generation += 1;
        lastKeys = keys;
        return generation;
    });

    let text = $state("");
    let who = $state<string | null>(null);
    const people = $derived.by(() => {
        const found: Record<string, Person & { count: number }> = {};
        for (const track of tracks) {
            if (!track.requester) continue;
            found[track.requester.id] ??= { ...track.requester, count: 0 };
            found[track.requester.id].count += 1;
        }
        return Object.values(found);
    });
    // Someone whose songs all left the queue stops being the filter
    const person = $derived(people.some((p) => p.id === who) ? who : null);
    // Applied once typing pauses, so the rows don't slide in and out on every keystroke. Clearing applies at once
    const FILTER_MS = 300;
    let needle = $state("");
    $effect(() => {
        const next = text.trim().toLocaleLowerCase();
        if (!next) {
            needle = "";
            return;
        }
        const timer = setTimeout(() => (needle = next), FILTER_MS);
        return () => clearTimeout(timer);
    });
    const filtering = $derived(!!needle || person !== null);
    const shown = $derived(
        tracks
            .map((track, index) => ({ track, index, key: keys[index] }))
            .filter(
                ({ track }) =>
                    (person === null || track.requester?.id === person) &&
                    (!needle || [track.title, track.author, track.requester?.name].some((field) => field?.toLocaleLowerCase().includes(needle))),
            ),
    );

    // Slides in from the right and out to the left while the row's height opens or closes, so the rest glide along.
    // No move animation on top: it pins leaving rows in place while the others slide over them
    function row(node: HTMLElement, { from }: { from: number }) {
        const height = node.offsetHeight;
        return {
            duration: 300,
            easing: cubicOut,
            css: (t: number, u: number) => `opacity: ${t}; transform: translateX(${u * from}px); height: ${t * height}px; overflow: hidden`,
        };
    }

    // Keyed by action and track, so only the button that was pressed spins
    const busy = new SvelteSet<string>();
    async function run(key: string, action: () => ReturnType<typeof control>) {
        if (busy.has(key)) return;
        busy.add(key);
        await action();
        busy.delete(key);
    }

    let target = $state<Person | null>(null);
    let confirming = $state(false);
    let removing = $state(false);
    const theirs = $derived(target ? tracks.filter((track) => track.requester?.id === target!.id) : []);
    const theirLength = $derived(theirs.reduce((sum, track) => sum + (track.isStream ? 0 : track.lengthMs), 0));
    const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? "" : "s"}`;

    function askRemove(person: Person) {
        target = person;
        confirming = true;
    }

    async function removeTheirs() {
        if (!target) return;
        const person = target;
        // Only the first page of the queue is loaded, so past it the exact count isn't known here
        const count = queue.total > tracks.length ? null : theirs.length;
        removing = true;
        const ok = await control(music.removeRequesterTracks({ guild, userId: person.id }));
        removing = false;
        if (!ok) return;
        confirming = false;
        toast.success(`Removed ${person.name}'s songs`, {
            description: count === null ? "Their songs left the queue" : `${plural(count, "song")} left the queue`,
            person,
        });
    }

    // Clearing and reversing touch everyone's songs, so both ask first
    let whole = $state<"clear" | "reverse" | null>(null);
    let wholeOpen = $state(false);
    let wholeBusy = $state(false);
    const loadedLength = $derived(tracks.reduce((sum, track) => sum + (track.isStream ? 0 : track.lengthMs), 0));

    function askWhole(kind: "clear" | "reverse") {
        whole = kind;
        wholeOpen = true;
    }

    async function runWhole() {
        if (!whole) return;
        wholeBusy = true;
        const ok = await control(whole === "clear" ? music.clearQueue({ guild }) : music.reverseQueue({ guild }), { announce: true });
        wholeBusy = false;
        if (ok) wholeOpen = false;
    }

    const action = "flex size-8 items-center justify-center rounded-full text-mist-300 transition-colors";
    const chip = "ripple flex h-8 items-center gap-2 rounded-full px-3 text-xs font-medium whitespace-nowrap transition-colors";
    const picked = "bg-accent/10 text-accent";
    const unpicked = "bg-surface-2 text-mist-400 hover:bg-surface-3 hover:text-mist-100";
    const neutral = [action, "hover:bg-surface-3 hover:text-mist-50"];
</script>

<section aria-labelledby="up-next" class="flex flex-col gap-2">
    <div class="flex items-center justify-between gap-4 px-2">
        <h2 id="up-next" class="font-display text-lg font-semibold">
            Up next <span class="font-mono text-sm font-normal text-mist-400">{queue.total}</span>
        </h2>
        {#if queue.total}
            <div class="flex gap-1">
                <Tooltip content={queue.total < 2 ? "Needs two songs or more" : "Reverse the queue"}>
                    <Button variant="ghost" icon aria-label="Reverse the queue" disabled={queue.total < 2} onclick={() => askWhole("reverse")}>
                        <MaterialSymbolsSwapVertRounded />
                    </Button>
                </Tooltip>
                <Tooltip content="Clear the queue">
                    <Button variant="ghost" icon aria-label="Clear the queue" onclick={() => askWhole("clear")}>
                        <MaterialSymbolsClearAllRounded />
                    </Button>
                </Tooltip>
            </div>
        {/if}
    </div>
    {#if tracks.length > 1}
        <div class="flex flex-col gap-2 px-2 pb-2">
            <Input
                type="search"
                icon={MaterialSymbolsSearchRounded}
                placeholder="Find in the queue"
                aria-label="Find in the queue"
                bind:value={text}
            />
            {#if people.length > 1}
                <ScrollRow role="radiogroup" aria-label="Added by">
                    <button
                        type="button"
                        role="radio"
                        aria-checked={person === null}
                        class={[chip, person === null ? picked : unpicked]}
                        {@attach ripple}
                        onclick={() => (who = null)}
                    >
                        Everyone
                    </button>
                    {#each people as p (p.id)}
                        <button
                            type="button"
                            role="radio"
                            aria-checked={person === p.id}
                            class={[chip, "pl-1", person === p.id ? picked : unpicked]}
                            {@attach ripple}
                            onclick={() => (who = person === p.id ? null : p.id)}
                        >
                            <Avatar src={p.avatarUrl} name={p.name} class="size-6 text-2xs" />{p.name}
                            <span class="font-mono opacity-60">{p.count}</span>
                        </button>
                    {/each}
                </ScrollRow>
            {/if}
        </div>
    {/if}
    {#if tracks.length}
        {#key order}
            <ol class="flex flex-col gap-1" in:fade={{ duration: 200 }} {@attach sortable({ onmove: reorder, disabled: () => filtering })}>
                {#each shown as { track, index, key } (key)}
                    {@const at = { guild, index, identifier: track.identifier }}
                    <li
                        in:row={{ from: 24 }}
                        out:row={{ from: -24 }}
                        data-sortable-index={index}
                        class="group relative flex items-center gap-2 rounded-2xl py-2 pr-2 transition-colors hover:bg-surface-2 data-dragging:z-10 data-dragging:bg-surface-3 data-dragging:shadow-xl data-dragging:shadow-black/50"
                    >
                        <Tooltip content={filtering ? "Clear the search and filter to reorder" : null}>
                            <button
                                type="button"
                                data-drag-handle
                                data-no-drag
                                aria-label="Reorder {track.title}. Use the arrow keys to move it."
                                aria-disabled={filtering}
                                class={[
                                    "flex h-12 w-8 shrink-0 touch-none items-center justify-center rounded-xl text-mist-400 transition-[color,opacity]",
                                    filtering ? "cursor-default opacity-40" : "cursor-grab hover:text-mist-50 active:cursor-grabbing",
                                ]}
                            >
                                <MaterialSymbolsDragIndicator class="size-5" />
                            </button>
                        </Tooltip>
                        <TrackRow {track}>
                            {#snippet trailing()}
                                {@const pending = busy.has(`jump:${track.identifier}`) || busy.has(`remove:${track.identifier}`)}
                                <span class="relative flex h-8 shrink-0 items-center justify-end">
                                    <span
                                        class={[
                                            "pr-2 font-mono text-xs text-mist-400 transition-opacity duration-200 ease-out group-focus-within:opacity-0 group-hover:opacity-0 pointer-coarse:hidden",
                                            pending && "opacity-0",
                                        ]}
                                    >
                                        {track.isStream ? "Live" : time(track.lengthMs)}
                                    </span>
                                    <span
                                        class={[
                                            "absolute -inset-y-2 right-0 flex items-center gap-1 bg-linear-to-r from-transparent via-surface-2 via-40% to-surface-2 pl-12 transition-opacity duration-200 ease-out group-focus-within:pointer-events-auto group-focus-within:opacity-100 group-hover:pointer-events-auto group-hover:opacity-100 group-data-dragging:via-surface-3 group-data-dragging:to-surface-3 pointer-coarse:pointer-events-auto pointer-coarse:static pointer-coarse:bg-none pointer-coarse:pl-0 pointer-coarse:opacity-100",
                                            pending ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
                                        ]}
                                    >
                                        <Tooltip content="Play now">
                                            <button
                                                type="button"
                                                aria-label="Play {track.title} now"
                                                aria-busy={busy.has(`jump:${track.identifier}`)}
                                                disabled={pending}
                                                class={neutral}
                                                onclick={() => run(`jump:${track.identifier}`, () => control(music.jumpToTrack(at)))}
                                            >
                                                {#if busy.has(`jump:${track.identifier}`)}<SvgSpinners90RingWithBg
                                                        class="size-4"
                                                    />{:else}<MaterialSymbolsPlayArrowRounded class="size-5" />{/if}
                                            </button>
                                        </Tooltip>
                                        {#if track.requester}
                                            {@const requester = track.requester}
                                            <Tooltip content="Remove every song {requester.name} added">
                                                <button
                                                    type="button"
                                                    aria-label="Remove every song {requester.name} added"
                                                    class={neutral}
                                                    disabled={pending}
                                                    onclick={() => askRemove(requester)}
                                                >
                                                    <MaterialSymbolsPersonRemoveRounded class="size-4" />
                                                </button>
                                            </Tooltip>
                                        {/if}
                                        <Tooltip content="Remove">
                                            <button
                                                type="button"
                                                aria-label="Remove {track.title}"
                                                aria-busy={busy.has(`remove:${track.identifier}`)}
                                                disabled={pending}
                                                class={[action, "hover:bg-red-400/10 hover:text-red-400"]}
                                                onclick={() => run(`remove:${track.identifier}`, () => control(music.removeTrack(at)))}
                                            >
                                                {#if busy.has(`remove:${track.identifier}`)}<SvgSpinners90RingWithBg
                                                        class="size-4 text-red-400"
                                                    />{:else}<MaterialSymbolsCloseRounded class="size-4" />{/if}
                                            </button>
                                        </Tooltip>
                                    </span>
                                </span>
                            {/snippet}
                        </TrackRow>
                    </li>
                {/each}
            </ol>
        {/key}
        {#if filtering && !shown.length}
            <p class="px-2 text-sm text-mist-400">No songs in the queue match.</p>
        {/if}
        {#if queue.total > tracks.length}
            <p class="px-2 text-xs text-mist-400">
                {filtering ? `Only the first ${tracks.length} songs are searched.` : `And ${queue.total - tracks.length} more.`}
            </p>
        {/if}
    {:else}
        <p class="px-2 text-sm text-mist-400">
            The queue is empty. Anything you add from search shows up here{autoplay ? ", and autoplay keeps the music going until then" : ""}.
        </p>
    {/if}

    {#if autoplay}
        <div class="mt-4 flex items-center gap-2 px-2">
            <MaterialSymbolsAutoplayRounded class="size-5 text-accent" />
            <h3 class="font-display text-lg font-semibold">Autoplay</h3>
            {#if queue.autoplay.length}<span class="font-mono text-sm text-mist-400">{queue.autoplay.length}</span>{/if}
        </div>
        {#if queue.autoplay.length}
            <p class="px-2 text-xs text-mist-400">Similar songs that play once the queue runs out.</p>
            <ol class="flex flex-col gap-1">
                {#each queue.autoplay as track, index (autoKeys[index])}
                    <li
                        in:row={{ from: 24 }}
                        out:row={{ from: -24 }}
                        class="flex items-center gap-4 rounded-2xl p-2 pl-10 transition-colors hover:bg-surface-2"
                    >
                        <TrackRow track={{ ...track, requester: null }}>
                            {#snippet trailing()}
                                <span class="shrink-0 pr-2 font-mono text-xs text-mist-400">{track.isStream ? "Live" : time(track.lengthMs)}</span>
                            {/snippet}
                        </TrackRow>
                    </li>
                {/each}
            </ol>
        {:else}
            <p class="px-2 text-xs text-mist-400">Related songs get picked automatically when the queue ends.</p>
        {/if}
    {/if}
</section>

<Dialog
    bind:open={() => confirming, (next) => !removing && (confirming = next)}
    title="Remove {target ? target.name + "'s" : 'their'} songs?"
    dismissable={!removing}
>
    {#if target}
        <div class="flex flex-col gap-4 text-sm">
            <div class="flex items-center gap-4 rounded-2xl bg-surface-2 p-4">
                <Avatar src={target.avatarUrl} name={target.name} class="size-12 text-lg" />
                <div class="flex min-w-0 flex-col">
                    <span class="truncate font-semibold">{target.name}</span>
                    <span class="text-xs text-mist-400">
                        {plural(theirs.length, "song")} in the queue{theirLength ? ` · ${time(theirLength)}` : ""}
                    </span>
                </div>
            </div>
            <ul class="flex flex-col gap-2">
                {#each theirs.slice(0, 5) as track, i (`${i}-${track.identifier}`)}
                    <li class="flex items-center gap-4">
                        <Cover src={track.artworkUrl} class="size-10 rounded-xl" />
                        <span class="flex min-w-0 flex-1 flex-col">
                            <span class="truncate font-medium">{track.title}</span>
                            <span class="truncate text-xs text-mist-400">{track.author}</span>
                        </span>
                        <span class="shrink-0 font-mono text-xs text-mist-400">{track.isStream ? "Live" : time(track.lengthMs)}</span>
                    </li>
                {/each}
            </ul>
            {#if theirs.length > 5}<p class="text-xs text-mist-400">And {plural(theirs.length - 5, "more song")}.</p>{/if}
            {#if queue.total > tracks.length}
                <p class="text-xs text-mist-400">Songs past the first {tracks.length} in the queue are removed too.</p>
            {/if}
        </div>
    {/if}
    {#snippet footer()}
        <Button variant="ghost" disabled={removing} onclick={() => (confirming = false)}>Cancel</Button>
        <Button variant="danger" loading={removing} onclick={removeTheirs}>
            {removing ? "Removing…" : `Remove ${plural(theirs.length, "song")}`}
        </Button>
    {/snippet}
</Dialog>

<Dialog
    bind:open={() => wholeOpen, (next) => !wholeBusy && (wholeOpen = next)}
    title={whole === "clear" ? "Clear the queue?" : "Reverse the queue?"}
    dismissable={!wholeBusy}
>
    <div class="flex flex-col gap-4 text-sm">
        {#if whole === "clear"}
            <div class="flex items-center gap-4 rounded-2xl bg-surface-2 p-4">
                <span class="flex shrink-0 -space-x-4">
                    {#each tracks.slice(0, 4) as track, i (`${i}-${track.identifier}`)}
                        <Cover src={track.artworkUrl} class="size-10 rounded-xl ring-2 ring-surface-2" />
                    {/each}
                </span>
                <span class="flex min-w-0 flex-col">
                    <span class="font-semibold">{plural(queue.total, "song")}</span>
                    {#if queue.total === tracks.length && loadedLength}<span class="text-xs text-mist-400">{time(loadedLength)} of music</span>{/if}
                </span>
            </div>
            <p class="text-mist-400">Every song in the queue goes, whoever added it. What's playing now keeps playing.</p>
        {:else if whole === "reverse" && tracks.length}
            {@const first = tracks[0]}
            {@const last = queue.total === tracks.length ? tracks.at(-1) : null}
            <p class="text-mist-400">The queue plays in the opposite order, so the last song comes up next.</p>
            <div class="flex flex-col gap-2 rounded-2xl bg-surface-2 p-4">
                {#if last}
                    <span class="text-2xs font-semibold tracking-wider text-accent uppercase">Up next after this</span>
                    <span class="flex items-center gap-4">
                        <Cover src={last.artworkUrl} class="size-10 rounded-xl" />
                        <span class="flex min-w-0 flex-col">
                            <span class="truncate font-medium">{last.title}</span>
                            <span class="truncate text-xs text-mist-400">{last.author}</span>
                        </span>
                    </span>
                {/if}
                <span class="text-2xs font-semibold tracking-wider text-mist-400 uppercase">Moves to the end</span>
                <span class="flex items-center gap-4">
                    <Cover src={first.artworkUrl} class="size-10 rounded-xl" />
                    <span class="flex min-w-0 flex-col">
                        <span class="truncate font-medium">{first.title}</span>
                        <span class="truncate text-xs text-mist-400">{first.author}</span>
                    </span>
                </span>
            </div>
        {/if}
    </div>
    {#snippet footer()}
        <Button variant="ghost" disabled={wholeBusy} onclick={() => (wholeOpen = false)}>Cancel</Button>
        {#if whole === "clear"}
            <Button variant="danger" loading={wholeBusy} onclick={runWhole}>{wholeBusy ? "Clearing…" : "Clear the queue"}</Button>
        {:else}
            <Button variant="primary" loading={wholeBusy} onclick={runWhole}>{wholeBusy ? "Reversing…" : "Reverse"}</Button>
        {/if}
    {/snippet}
</Dialog>
