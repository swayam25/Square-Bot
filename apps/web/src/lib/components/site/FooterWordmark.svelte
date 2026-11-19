<script module lang="ts">
    import { blobPath } from "#lib/shape.ts";

    // Saira 700 at 300 units: advances measured in the browser, letter tops sit at y 213 on a 420 baseline
    const LETTERS = [
        ["S", 0],
        ["Q", 185],
        ["U", 396],
        ["A", 603],
        ["R", 810],
        ["E", 1012],
    ] as const;
    const BASE = 420;

    const beat = blobPath(10, 0.1, 95, 169, 46);
    const peek = blobPath(4, 0.12, 290, 222, 50);
    const dash = blobPath(7, 0.1, 498, 356, 25);
    const star = blobPath(5, 0.22, 706, 174, 48);
    const pip = blobPath(6, 0.12, 895, 183, 34);
    const guard = blobPath(8, 0.1, 1130, 183, 32);
    const sparkle = (x: number, y: number, size: number) => blobPath(4, 0.45, x, y, size);
</script>

<script lang="ts">
    import type { Component } from "svelte";
    import MaterialSymbolsCelebrationRounded from "~icons/material-symbols/celebration-rounded";
    import MaterialSymbolsFavoriteRounded from "~icons/material-symbols/favorite-rounded";
    import MaterialSymbolsForumRounded from "~icons/material-symbols/forum-rounded";
    import MaterialSymbolsLinkRounded from "~icons/material-symbols/link-rounded";
    import MaterialSymbolsMusicNoteRounded from "~icons/material-symbols/music-note-rounded";
    import MaterialSymbolsShieldRounded from "~icons/material-symbols/shield-rounded";
    import MaterialSymbolsStarRounded from "~icons/material-symbols/star-rounded";

    const clip = $props.id();

    const stickers: { icon: Component; x: number; y: number; size: number; turn: number; ink: string }[] = [
        { icon: MaterialSymbolsMusicNoteRounded, x: 150, y: 76, size: 40, turn: 12, ink: "text-accent" },
        { icon: MaterialSymbolsMusicNoteRounded, x: 18, y: 104, size: 28, turn: -14, ink: "text-violet-300" },
        { icon: MaterialSymbolsCelebrationRounded, x: 368, y: 104, size: 38, turn: -10, ink: "text-pink-400" },
        { icon: MaterialSymbolsStarRounded, x: 606, y: 98, size: 30, turn: 15, ink: "text-amber-400" },
        { icon: MaterialSymbolsStarRounded, x: 786, y: 70, size: 22, turn: -8, ink: "text-amber-300" },
        { icon: MaterialSymbolsFavoriteRounded, x: 1000, y: 92, size: 32, turn: 10, ink: "text-red-400" },
        { icon: MaterialSymbolsForumRounded, x: 1150, y: 76, size: 34, turn: -8, ink: "text-emerald-400" },
    ];
</script>

{#snippet eyes(x: number, y: number, gap: number, size: number, lookX = 0, lookY = 0)}
    {#each [x - gap, x + gap] as eye (eye)}
        <ellipse cx={eye} cy={y} rx={size * 0.8} ry={size} class="fill-white" />
        <circle cx={eye + lookX} cy={y + lookY} r={size * 0.55} class="fill-gray-950" />
        <circle cx={eye + lookX - size * 0.2} cy={y + lookY - size * 0.25} r={size * 0.18} class="fill-white" />
    {/each}
{/snippet}

{#snippet smile(x: number, y: number, width: number)}
    <path d="M{x - width} {y} q{width} {width * 0.9} {width * 2} 0" class="fill-none stroke-gray-950" stroke-width="4" stroke-linecap="round" />
{/snippet}

{#snippet blush(x: number, y: number, gap: number)}
    <ellipse cx={x - gap} cy={y} rx="6" ry="3.5" class="fill-pink-300/50" />
    <ellipse cx={x + gap} cy={y} rx="6" ry="3.5" class="fill-pink-300/50" />
{/snippet}

<svg viewBox="0 48 1200 414" aria-hidden="true" class="block w-full select-none">
    {#each stickers as sticker, index (index)}
        <g transform="translate({sticker.x} {sticker.y}) rotate({sticker.turn} {sticker.size / 2} {sticker.size / 2}) scale({sticker.size / 24})">
            <sticker.icon style="width: 24px; height: 24px" class={sticker.ink} />
        </g>
    {/each}
    <path d={sparkle(244, 96, 9)} class="fill-white/40" />
    <path d={sparkle(560, 150, 8)} class="fill-accent/70" />
    <path d={sparkle(1064, 62, 9)} class="fill-amber-300/70" />
    <path d={sparkle(470, 70, 6)} class="fill-violet-300/60" />

    <!-- Peek hides behind the Q, so it's drawn before the letters. The clip keeps it out of the Q's hole -->
    <clipPath id={clip}><rect x="220" y="100" width="140" height="151" /></clipPath>
    <g clip-path="url(#{clip})"><path d={peek} class="fill-pink-400" /></g>
    {@render eyes(290, 199, 16, 9, -3, -2)}
    <g transform="rotate(-5 290 186)">
        <path d="M270 186 L290 122 L310 186 Z" class="fill-amber-400" />
        <path d="M280 165 L300 165 M284 146 L296 146" class="stroke-white/70" stroke-width="5" stroke-linecap="round" />
        <circle cx="290" cy="120" r="8" class="fill-white" />
    </g>

    {#each LETTERS as [letter, x] (letter)}
        <text {x} y={BASE} class="fill-gray-800 font-display text-[300px] font-bold">{letter}</text>
    {/each}

    <circle cx="258" cy="214" r="11" class="fill-pink-400" />
    <circle cx="322" cy="214" r="11" class="fill-pink-400" />

    <path d="M47 169 A48 48 0 0 1 143 169" class="fill-none stroke-violet-300" stroke-width="8" stroke-linecap="round" />
    <path d={beat} class="fill-accent" />
    <rect x="37" y="151" width="20" height="40" rx="9" class="fill-violet-400" />
    <rect x="133" y="151" width="20" height="40" rx="9" class="fill-violet-400" />
    <path d="M73 164 q7 -9 14 0 M103 164 q7 -9 14 0" class="fill-none stroke-gray-950" stroke-width="4.5" stroke-linecap="round" />
    {@render smile(95, 180, 8)}
    {@render blush(95, 176, 26)}

    <path d={dash} class="fill-violet-400" />
    {@render eyes(498, 350, 9, 7, 2, -3)}

    <g transform="rotate(-6 706 174)">
        <path d={star} class="fill-amber-400" />
        {@render eyes(706, 172, 13, 8, -2, 0)}
        {@render smile(706, 188, 7)}
    </g>

    <path d="M922 172 Q940 160 942 142" class="fill-none stroke-emerald-400" stroke-width="10" stroke-linecap="round" />
    <g transform="translate(918 112) rotate(-20 24 24) scale(2)">
        <MaterialSymbolsLinkRounded style="width: 24px; height: 24px" class="text-gray-100" />
    </g>
    <circle cx="942" cy="138" r="9" class="fill-emerald-400" />
    <path d={pip} class="fill-emerald-400" />
    {@render eyes(895, 178, 11, 7, 1, -1)}
    {@render smile(895, 192, 6)}
    {@render blush(895, 190, 20)}

    <path d={guard} class="fill-red-400" />
    {@render eyes(1124, 178, 11, 7, -1, 1)}
    <path d="M1106 165 l11 4 M1142 165 l-11 4" class="stroke-gray-950" stroke-width="4" stroke-linecap="round" />
    <g transform="translate(1144 186) scale(1.25)">
        <MaterialSymbolsShieldRounded style="width: 24px; height: 24px" class="text-gray-100" />
    </g>
</svg>
