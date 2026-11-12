<script lang="ts">
    import Button from "#lib/components/ui/Button.svelte";
    import OverlayScrollbar from "#lib/components/ui/OverlayScrollbar.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { trackLyrics } from "#lib/lyrics.remote.ts";
    import { glyphsOf, linesAt, sungLines, type SungLine } from "#lib/lyrics.ts";
    import * as music from "#lib/music.remote.ts";
    import type { Track } from "@square/api-client";
    import { untrack } from "svelte";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import MaterialSymbolsLyricsRounded from "~icons/material-symbols/lyrics-rounded";
    import MaterialSymbolsMusicNoteRounded from "~icons/material-symbols/music-note-rounded";
    import MaterialSymbolsMyLocationRounded from "~icons/material-symbols/my-location-rounded";
    import MaterialSymbolsRemoveRounded from "~icons/material-symbols/remove-rounded";
    import { lyricsSync, nudgeSync, SYNC_LIMIT_MS, SYNC_STEP_MS, syncLabel } from "./lyrics-sync.svelte.ts";
    import { control } from "./player.ts";

    let {
        guild,
        track,
        position: playhead,
        playing,
        zen = false,
    }: { guild: string; track: Track; position: number; playing: boolean; zen?: boolean } = $props();

    // Lyrics time, after the listener's sync nudge
    const offset = $derived(lyricsSync.offset);
    const position = $derived(playhead - offset);

    // The rounded music note's path, inline so the liquid can fill it
    const NOTE =
        "M7.175 19.825Q6 18.65 6 17t1.175-2.825T10 13q.575 0 1.063.138t.937.412V4q0-.425.288-.712T13 3h4q.425 0 .713.288T18 4v2q0 .425-.288.713T17 7h-3v10q0 1.65-1.175 2.825T10 21t-2.825-1.175";

    const ANCHOR = 0.33;
    const RESUME_MS = 4000;
    // Lyrics run a touch ahead of the audio so they never read as late, and the view glides to a line before it's sung
    const LEAD_MS = 115;
    const SCROLL_LEAD_MS = 500;
    const ENDING_MS = 500;
    // The band the view keeps lines inside, as shares of its height (the edges fade out)
    const BAND_TOP = 0.12;
    const BAND_BOTTOM = 0.82;
    const GLOW_MS = 1200;
    const GLOW_REST = 0.2;
    const SETTLE_MS = 500;

    const lyricsQuery = $derived(trackLyrics({ title: track.title, artist: track.author, durationMs: track.lengthMs }));
    const lyrics = $derived(lyricsQuery.current);
    const lines = $derived<SungLine[]>(lyrics ? sungLines(lyrics, track.lengthMs) : []);

    const t = $derived(position + LEAD_MS);
    // Joined into strings so these only change with the lines, not on every frame
    const currentKey = $derived(linesAt(lines, t).join());
    const current = $derived(currentKey ? currentKey.split(",").map(Number) : []);
    const active = $derived(current.at(-1) ?? -1);
    const focusKey = $derived.by(() => {
        const list = linesAt(lines, position, SCROLL_LEAD_MS);
        return list.filter((i, n) => n === list.length - 1 || position < lines[i].end - ENDING_MS).join();
    });
    const focus = $derived(focusKey ? focusKey.split(",").map(Number) : [0]);
    // The line the singer is on: the latest still running, the rest are tails
    const anchor = $derived.by(() => {
        const started = focus.filter((i) => lines[i] && lines[i].start <= position);
        return started.findLast((i) => position < lines[i].end) ?? started.at(-1) ?? focus[0];
    });

    const noteId = $props.id();
    let scroller = $state<HTMLElement>();
    let plainScroller = $state<HTMLElement | null>(null);
    let browsing = $state(false);
    let idle: ReturnType<typeof setTimeout> | undefined;
    let frame = 0;
    let last = 0;
    let target = 0;
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");

    const clamp = (v: number) => Math.min(1, Math.max(0, v));
    const progress = (start: number, end: number) => clamp((t - start) / Math.max(1, end - start));
    // Bright as a letter lights, fading to the line's resting glow. Zero until it starts, so dim letters stay dim.
    const glow = (lit: number, start: number, wordMs: number) =>
        lit * (GLOW_REST + (1 - GLOW_REST) * clamp(1 - (t - start) / Math.max(GLOW_MS, wordMs * 1.2)));
    // Rises as it lights, crests when fully lit, then settles part of the way back
    const lift = (lit: number, end: number) => (lit < 1 ? lit * lit * (3 - 2 * lit) : 0.4 + 0.6 * clamp(1 - (t - end) / SETTLE_MS));

    // The liquid in the interlude note: its surface rises with `level` and its waves flatten as it fills
    function wavePath(level: number, phase: number) {
        const y = 23 - level * 24;
        const a = 1.4 * (1 - level) + 0.15;
        const x0 = -8 + (phase % 8);
        let d = `M ${x0} ${y}`;
        for (let x = x0; x < 32; x += 8) d += ` Q ${x + 2} ${y - a} ${x + 4} ${y} T ${x + 8} ${y}`;
        return `${d} L 32 26 L -8 26 Z`;
    }

    function targetFor(indices: number[], lead: number) {
        const view = scroller;
        if (!view) return 0;
        const box = view.getBoundingClientRect();
        const place = (index: number) => {
            const line = view.querySelector<HTMLElement>(`[data-line="${index}"]`);
            if (!line) return null;
            const rect = line.getBoundingClientRect();
            const top = view.scrollTop + rect.top - box.top;
            return { top, bottom: top + rect.height, middle: top + rect.height / 2 };
        };
        const placed = indices.map(place).filter((p) => p !== null);
        const main = place(lead) ?? placed.at(-1);
        if (!main) return 0;
        const height = view.clientHeight;
        const above = height * BAND_TOP;
        const below = height * BAND_BOTTOM;
        const middle = placed.reduce((total, p) => total + p.middle, 0) / placed.length;
        let y = middle - height * ANCHOR;
        y = Math.max(y, placed.at(-1)!.bottom - below);
        y = Math.min(y, placed[0].top - above);
        y = Math.max(y, main.bottom - below);
        y = Math.min(y, main.top - above);
        return Math.max(0, y);
    }

    // A critically damped glide, so the view eases into each line without overshooting
    function follow(indices: number[], lead: number, instant: boolean) {
        const view = scroller;
        if (!view) return;
        target = targetFor(indices, lead);
        if (instant || reduced.matches) {
            cancelAnimationFrame(frame);
            frame = 0;
            view.scrollTop = target;
            return;
        }
        const step = (now: number) => {
            const dt = last ? Math.min(0.05, (now - last) / 1000) : 1 / 60;
            last = now;
            const gap = target - view.scrollTop;
            if (Math.abs(gap) < 0.5) {
                view.scrollTop = target;
                frame = 0;
                last = 0;
                return;
            }
            view.scrollTop += gap * (1 - Math.exp(-dt * 9));
            frame = requestAnimationFrame(step);
        };
        if (!frame) frame = requestAnimationFrame(step);
    }

    function browse() {
        cancelAnimationFrame(frame);
        frame = 0;
        last = 0;
        browsing = true;
        clearTimeout(idle);
        idle = setTimeout(resume, RESUME_MS);
    }

    function resume() {
        clearTimeout(idle);
        browsing = false;
        follow(focus, anchor, false);
    }

    let shown: SungLine[] | null = null;
    $effect(() => {
        const indices = focus;
        const lead = anchor;
        const fresh = lines !== shown;
        if (!scroller || browsing) return;
        untrack(() => {
            follow(indices, lead, fresh);
            shown = lines;
        });
    });

    function onkeydown(event: KeyboardEvent) {
        if (["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "].includes(event.key)) browse();
    }

    const watch = (node: HTMLElement) => {
        const observer = new ResizeObserver(() => {
            if (!browsing) follow(focus, anchor, true);
        });
        observer.observe(node);
        const press = (event: PointerEvent) => event.target === node && browse();
        node.addEventListener("wheel", browse, { passive: true });
        node.addEventListener("touchmove", browse, { passive: true });
        node.addEventListener("keydown", onkeydown);
        node.addEventListener("pointerdown", press);
        return () => {
            node.removeEventListener("wheel", browse);
            node.removeEventListener("touchmove", browse);
            node.removeEventListener("keydown", onkeydown);
            node.removeEventListener("pointerdown", press);
            observer.disconnect();
            cancelAnimationFrame(frame);
            clearTimeout(idle);
        };
    };

    const canSeek = $derived(!track.isStream);
    // A tapped line seeks to where it sits in the song once the nudge is taken into account
    const seek = (start: number) => control(music.seekTrack({ guild, positionMs: Math.max(0, Math.round(start + offset)) }));
</script>

{#snippet sung(part: SungLine, on: boolean)}
    {#if on}
        {#each glyphsOf(part) as g, k (k)}
            {@const wordMs = part.timed ? g.end - g.start : 0}
            {#if g.letters}
                <span class="word"
                    >{#each g.letters as c, j (j)}
                        {@const lit = progress(c.start, c.end)}
                        <span class="glyph" style:--l={lit} style:--g={glow(lit, c.start, wordMs)} style:--y={lit > 0 ? lift(lit, c.end) : 0}
                            >{c.text}</span
                        >
                    {/each}</span
                >{g.tail}
            {:else}
                {@const lit = progress(g.start, g.end)}
                <span class="sweep" style:--p={lit} style:--g={glow(lit, g.start, wordMs)}>{g.text}</span>{g.tail}
            {/if}
        {/each}
    {:else}
        {part.text}
    {/if}
{/snippet}

{#snippet empty(icon: typeof MaterialSymbolsLyricsRounded, title: string, text: string)}
    {@const Icon = icon}
    <div class="flex flex-1 flex-col items-center justify-center gap-2 p-10 text-center">
        <span class="mb-2 flex size-14 items-center justify-center rounded-2xl bg-surface-2 text-mist-100"><Icon class="size-7" /></span>
        <p class="font-display text-lg font-semibold">{title}</p>
        <p class="text-sm text-mist-400">{text}</p>
    </div>
{/snippet}

{#if lyrics?.instrumental}
    {@render empty(MaterialSymbolsMusicNoteRounded, "Instrumental", "Nothing to sing along to.")}
{:else if lyrics && lines.length}
    <div class="relative flex min-h-0 flex-1 flex-col">
        <div
            bind:this={scroller}
            class={["lyrics min-h-0 flex-1 overflow-y-auto overscroll-contain", browsing && "browsing", zen && "zen"]}
            role="region"
            aria-label="Lyrics"
            tabindex="-1"
            {@attach watch}
        >
            <div class="h-[33cqh]" aria-hidden="true"></div>
            <ol class="flex flex-col gap-1 px-4 md:px-6">
                {#each lines as line, i (i)}
                    {@const distance = Math.min(Math.abs(i - active), 6)}
                    {@const on = current.includes(i)}
                    <li data-line={i}>
                        {#if line.interlude}
                            {@const fill = on ? progress(line.start, line.end - 450) : 0}
                            <div
                                class={["note", on && "on"]}
                                style:--p={fill}
                                style:--breath={on && playing ? 1 + 0.06 * Math.sin(t / 380) : 1}
                                style:--exit={on ? clamp((line.end - t) / 450) : 0}
                                aria-hidden="true"
                            >
                                <svg viewBox="0 0 24 24">
                                    {#if on}
                                        <defs>
                                            <clipPath id="{noteId}-{i}"><path d={wavePath(fill, t / 160)} /></clipPath>
                                        </defs>
                                    {/if}
                                    <path class="base" d={NOTE} />
                                    {#if on}
                                        <!-- The glow sits on the group, so it follows the liquid -->
                                        <g class="lit"><path d={NOTE} clip-path="url(#{noteId}-{i})" /></g>
                                    {/if}
                                </svg>
                            </div>
                        {:else}
                            <button
                                type="button"
                                dir="auto"
                                class={["line", on && "on"]}
                                style:--d={distance}
                                disabled={!canSeek}
                                aria-current={on ? "true" : undefined}
                                onclick={() => seek(line.start)}
                            >
                                {@render sung(line, on)}
                                {#if line.background}<span class="background">{@render sung(line.background, on)}</span>{/if}
                            </button>
                        {/if}
                    </li>
                {/each}
            </ol>
            <div class="h-[60cqh]" aria-hidden="true"></div>
        </div>

        {#if browsing}
            <div class="pointer-events-none absolute inset-x-0 bottom-10 flex justify-center">
                <Button class="pointer-events-auto animate-pop-in shadow-xl shadow-black/50" onclick={resume}>
                    <MaterialSymbolsMyLocationRounded />Back to now
                </Button>
            </div>
        {/if}
        {#if !zen}
            <div class="flex items-center justify-between gap-4 px-4 pt-2 pb-4 text-xs text-mist-400 md:px-6">
                <p>Lyrics from {lyrics.source}</p>
                <!-- Only for this visit: a reload puts it back to 0 -->
                <div role="group" aria-label="Lyrics sync" class="flex items-center gap-1">
                    <span class="mr-1 font-medium">Sync</span>
                    <Tooltip content="Show lyrics {SYNC_STEP_MS / 1000}s earlier">
                        <button
                            type="button"
                            aria-label="Show lyrics {SYNC_STEP_MS / 1000}s earlier"
                            disabled={offset <= -SYNC_LIMIT_MS}
                            class="flex size-8 items-center justify-center rounded-full text-mist-300 transition-colors hover:bg-surface-2 hover:text-mist-50 disabled:opacity-40"
                            onclick={() => nudgeSync(-SYNC_STEP_MS)}
                        >
                            <MaterialSymbolsRemoveRounded class="size-4" />
                        </button>
                    </Tooltip>
                    <Tooltip content={offset === 0 ? "In sync with the song" : "Reset sync"}>
                        <button
                            type="button"
                            aria-label={offset === 0 ? "Lyrics in sync with the song" : `Lyrics shifted ${syncLabel(offset)}, reset`}
                            aria-live="polite"
                            disabled={offset === 0}
                            class={[
                                "h-8 min-w-14 rounded-full px-2 font-mono text-xs tabular-nums transition-colors enabled:hover:bg-surface-2",
                                offset === 0 ? "text-mist-400" : "text-accent",
                            ]}
                            onclick={() => (lyricsSync.offset = 0)}>{syncLabel(offset)}</button
                        >
                    </Tooltip>
                    <Tooltip content="Show lyrics {SYNC_STEP_MS / 1000}s later">
                        <button
                            type="button"
                            aria-label="Show lyrics {SYNC_STEP_MS / 1000}s later"
                            disabled={offset >= SYNC_LIMIT_MS}
                            class="flex size-8 items-center justify-center rounded-full text-mist-300 transition-colors hover:bg-surface-2 hover:text-mist-50 disabled:opacity-40"
                            onclick={() => nudgeSync(SYNC_STEP_MS)}
                        >
                            <MaterialSymbolsAddRounded class="size-4" />
                        </button>
                    </Tooltip>
                </div>
            </div>
        {/if}
    </div>
{:else if lyrics}
    <div class="relative flex min-h-0 flex-1 flex-col">
        <div class="relative min-h-0 flex-1">
            <div bind:this={plainScroller} class="size-full overflow-y-auto overscroll-contain px-4 pb-6 md:px-6">
                <p class="font-display text-xl leading-relaxed font-semibold whitespace-pre-line text-mist-100">
                    {lyrics.lines.map((line) => line.text).join("\n")}
                </p>
            </div>
            <OverlayScrollbar viewport={plainScroller} inset={16} />
        </div>
        {#if !zen}
            <div class="flex h-14 items-center justify-between gap-4 px-4 pt-2 pb-4 text-xs text-mist-400 md:px-6">
                <p>Lyrics from {lyrics.source}</p>
                <p class="font-medium">Not synced to the song</p>
            </div>
        {/if}
    </div>
{:else if lyricsQuery.error}
    {@render empty(
        MaterialSymbolsLyricsRounded,
        "Couldn't load lyrics",
        lyricsQuery.error.status === 429 ? lyricsQuery.error.message : "The lyrics service didn't answer.",
    )}
{:else if lyrics === null}
    {@render empty(MaterialSymbolsLyricsRounded, "No lyrics for this one", "BetterLyrics and LRCLIB don't have this song yet.")}
{:else}
    <div class="flex flex-col gap-4 p-6" aria-label="Loading lyrics" role="status">
        {#each [78, 62, 86, 54, 70] as width, i (i)}
            <span class="h-7 animate-pulse rounded-full bg-surface-2" style:width="{width}%" style:animation-delay="{i * 120}ms"></span>
        {/each}
    </div>
{/if}

<style>
    .lyrics {
        container-type: size;
        scrollbar-width: none;
        mask-image: linear-gradient(to bottom, transparent, #000 12%, #000 82%, transparent);
    }
    .lyrics::-webkit-scrollbar {
        display: none;
    }

    .line {
        --glow: var(--color-white);
        display: block;
        width: 100%;
        border-radius: var(--radius-2xl);
        padding: 0.375rem 0.75rem;
        text-align: start;
        font-family: var(--font-display);
        font-size: var(--text-2xl);
        line-height: 1.3;
        font-weight: 700;
        color: color-mix(in srgb, var(--color-mist-50) 36%, transparent);
        transform-origin: left center;
        scale: 0.95;
        filter: blur(calc(var(--d, 0) * 0.4px));
        transition:
            scale 500ms var(--ease-smooth),
            filter 600ms ease-out,
            color 600ms ease-out,
            background-color 200ms ease-out;
    }
    @media (width >= 48rem) {
        .line {
            font-size: var(--text-3xl);
        }
    }
    .zen .line {
        font-size: var(--text-3xl);
    }
    @media (width >= 64rem) {
        .zen .line {
            font-size: var(--text-5xl);
        }
    }
    .line.on {
        scale: 1;
        color: var(--color-mist-50);
        filter: none;
    }
    .line:enabled {
        cursor: pointer;
    }
    .line:enabled:hover,
    .browsing .line {
        filter: none;
    }
    .line:enabled:hover {
        background-color: var(--color-surface-2);
    }
    .zen .line:enabled:hover {
        background-color: color-mix(in srgb, var(--color-white) 8%, transparent);
    }
    .line:enabled:hover:not(.on) {
        color: color-mix(in srgb, var(--color-mist-50) 64%, transparent);
    }

    /* Letters light up as they're sung: each fades in, pops a hair, rises to crest and settles, glowing brightly at
       first and fading to a soft glow. Transparent until a letter starts, so unlit letters stay dim. */
    .word {
        display: inline-block;
        white-space: nowrap;
    }
    .glyph {
        display: inline-block;
        white-space: pre;
        transform-origin: 50% 100%;
        color: color-mix(in srgb, var(--color-mist-50) calc(36% + 64% * var(--l)), transparent);
        translate: 0 calc(var(--y) * -0.05em);
        scale: calc(1 + 0.04 * var(--l) * (1 - var(--l)) * 4);
        text-shadow:
            0 0 calc(var(--g) * 0.8rem) color-mix(in srgb, var(--glow) calc(var(--g) * 70%), transparent),
            0 0 calc(var(--g) * 0.25rem) color-mix(in srgb, var(--glow) calc(var(--g) * 45%), transparent);
    }

    .background {
        display: block;
        margin-top: 0.15em;
        font-size: 0.68em;
        font-weight: 600;
        opacity: 0.8;
    }

    /* Joining and RTL scripts fill word by word with a soft leading edge, so their shaping and order stay intact */
    .sweep {
        --edge: 0.5em;
        --sweep-dir: 90deg;
        display: inline-block;
        background-image: linear-gradient(
            var(--sweep-dir),
            var(--color-mist-50) calc(var(--p) * (100% + var(--edge)) - var(--edge)),
            color-mix(in srgb, var(--color-mist-50) 36%, transparent) calc(var(--p) * (100% + var(--edge)))
        );
        background-clip: text;
        -webkit-background-clip: text;
        color: transparent;
        filter: drop-shadow(0 0 calc(var(--g) * 0.6rem) color-mix(in srgb, var(--glow) calc(var(--g) * 70%), transparent));
    }
    .sweep:dir(rtl) {
        --sweep-dir: 270deg;
    }

    /* Instrumental gaps: a note that fills with glowing liquid, its rippling surface flattening as it rises,
       breathing gently, then shrinking away as the singing returns */
    .note {
        --glow: var(--color-white);
        width: 3.5rem;
        height: 3.5rem;
        margin-inline: 0.25rem;
        transform-origin: 30% 80%;
        scale: 0;
        opacity: 0;
        transition:
            scale 500ms var(--ease-spring),
            opacity 300ms ease-out;
    }
    .note.on {
        scale: calc(var(--breath) * var(--exit));
        opacity: 1;
        transition: opacity 300ms ease-out;
    }
    .note svg {
        width: 100%;
        height: 100%;
        overflow: visible;
    }
    .note .base {
        fill: color-mix(in srgb, var(--color-mist-50) 30%, transparent);
    }
    .note .lit {
        fill: var(--color-mist-50);
        filter: drop-shadow(0 0 calc(2px + var(--p) * 6px) color-mix(in srgb, var(--glow) 70%, transparent));
    }

    @media (prefers-reduced-motion: reduce) {
        .line,
        .note {
            transition: none;
            filter: none;
        }
        .glyph {
            translate: none;
            scale: none;
        }
        .note.on {
            scale: var(--exit);
        }
    }
</style>
