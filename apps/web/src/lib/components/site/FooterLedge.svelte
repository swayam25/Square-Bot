<script module lang="ts">
    import { blobPath } from "#lib/shape.ts";

    // Mascot seats depend on this wave: crests (y 162) at x 100, 420, 740, troughs (y 174) at 260, 580, 900.
    // It runs far past the viewBox so the ledge reaches the screen edges.
    const EDGE = 168;
    const HALF = 160;
    const START = 20 - HALF * 28;
    let d = `M${START} ${EDGE} Q${START + HALF / 2} ${EDGE - 12} ${START + HALF} ${EDGE}`;
    for (let x = START + HALF; x < 5400; x += HALF) d += `T${x + HALF} ${EDGE}`;
    const LEDGE = `${d}V200H${START}Z`;

    const beat = blobPath(10, 0.1, 100, 129, 44);
    const peek = blobPath(4, 0.12, 260, 186, 46);
    const dash = blobPath(7, 0.1, 420, 140, 30);
    const star = blobPath(5, 0.22, 580, 149, 48);
    const pip = blobPath(6, 0.12, 740, 137, 34);
    const guard = blobPath(8, 0.1, 900, 149, 34);
    const sparkle = (x: number, y: number, size: number) => blobPath(4, 0.45, x, y, size);
</script>

<script lang="ts">
    import type { Attachment } from "svelte/attachments";
    import MaterialSymbolsLinkRounded from "~icons/material-symbols/link-rounded";
    import MaterialSymbolsMusicNoteRounded from "~icons/material-symbols/music-note-rounded";
    import MaterialSymbolsShieldRounded from "~icons/material-symbols/shield-rounded";

    const clip = $props.id();

    let awake = $state(false);

    const watch: Attachment<SVGSVGElement> = (node) => {
        const observer = new IntersectionObserver(([entry]) => (awake = entry.isIntersecting));
        observer.observe(node);
        return () => observer.disconnect();
    };
</script>

{#snippet eyes(x: number, y: number, gap: number, size: number, lookX: number, lookY: number, delay: number)}
    <g class="blink" style:animation-delay="{delay}s">
        {#each [x - gap, x + gap] as eye (eye)}
            <ellipse cx={eye} cy={y} rx={size * 0.8} ry={size} class="fill-white" />
            <circle cx={eye + lookX} cy={y + lookY} r={size * 0.55} class="fill-gray-950" />
            <circle cx={eye + lookX - size * 0.2} cy={y + lookY - size * 0.25} r={size * 0.18} class="fill-white" />
        {/each}
    </g>
{/snippet}

{#snippet smile(x: number, y: number, width: number)}
    <path d="M{x - width} {y} q{width} {width * 0.9} {width * 2} 0" class="fill-none stroke-gray-950" stroke-width="4" stroke-linecap="round" />
{/snippet}

{#snippet blush(x: number, y: number, gap: number)}
    <ellipse cx={x - gap} cy={y} rx="6" ry="3.5" class="fill-pink-300/50" />
    <ellipse cx={x + gap} cy={y} rx="6" ry="3.5" class="fill-pink-300/50" />
{/snippet}

{#snippet legs(x: number, seat: number, gap: number, fill: string)}
    <rect x={x - gap - 6} y={seat - 6} width="12" height="26" rx="6" class={fill} />
    <rect x={x + gap - 6} y={seat - 6} width="12" height="26" rx="6" class={fill} />
{/snippet}

<svg
    viewBox="0 20 1000 180"
    aria-hidden="true"
    {@attach watch}
    data-awake={awake || undefined}
    class="-mb-px block h-auto w-full overflow-visible select-none"
>
    <path d={sparkle(40, 70, 5)} class="fill-white/20" />
    <path d={sparkle(190, 56, 7)} class="fill-white/30" />
    <path d={sparkle(490, 44, 6)} class="fill-accent/60" />
    <path d={sparkle(660, 76, 8)} class="fill-amber-300/50" />
    <path d={sparkle(850, 50, 6)} class="fill-violet-300/50" />
    <path d={sparkle(980, 96, 6)} class="fill-pink-300/40" />

    <!-- Must stay before the ledge path, which hides Peek when it ducks -->
    <g class="peek">
        <rect x="210" y="76" width="100" height="100" fill="transparent" />
        <clipPath id={clip}><rect x="190" y="20" width="140" height="170" /></clipPath>
        <g clip-path="url(#{clip})">
            <g class="peek-head">
                <path d={peek} class="fill-pink-400" />
                {@render eyes(260, 166, 15, 9, -2, -3, -1.5)}
                <g transform="rotate(-5 260 146)">
                    <path d="M240 150 L260 88 L280 150 Z" class="fill-amber-400" />
                    <path d="M250 130 L270 130 M254 111 L266 111" class="stroke-white/70" stroke-width="5" stroke-linecap="round" />
                    <circle cx="260" cy="86" r="8" class="fill-white" />
                </g>
            </g>
        </g>
    </g>

    <path d={LEDGE} class="fill-gray-900" />

    <g class="peek-hands">
        <circle cx="228" cy="173" r="11" class="fill-pink-400" />
        <circle cx="292" cy="173" r="11" class="fill-pink-400" />
    </g>

    <g class="beat">
        <rect x="48" y="44" width="110" height="131" fill="transparent" />
        <g class="note">
            <g transform="translate(130 44) rotate(12 14 14) scale(1.2)">
                <MaterialSymbolsMusicNoteRounded style="width: 24px; height: 24px" class="text-accent" />
            </g>
        </g>
        {@render legs(100, 162, 16, "fill-accent")}
        <g class="beat-head">
            <path d="M52 129 A48 48 0 0 1 148 129" class="fill-none stroke-violet-300" stroke-width="8" stroke-linecap="round" />
            <path d={beat} class="fill-accent" />
            <rect x="42" y="111" width="20" height="40" rx="9" class="fill-violet-400" />
            <rect x="138" y="111" width="20" height="40" rx="9" class="fill-violet-400" />
            <path d="M78 124 q7 -9 14 0 M108 124 q7 -9 14 0" class="fill-none stroke-gray-950" stroke-width="4.5" stroke-linecap="round" />
            {@render smile(100, 140, 8)}
            {@render blush(100, 136, 26)}
        </g>
    </g>

    <g class="dash">
        <rect x="386" y="104" width="68" height="82" fill="transparent" />
        <g class="dash-body">
            {@render legs(420, 162, 10, "fill-violet-400")}
            <path d={dash} class="fill-violet-400" />
            {@render eyes(420, 136, 9, 7, 2, -3, -3)}
            {@render smile(420, 150, 5)}
        </g>
    </g>

    <g class="star">
        <rect x="528" y="76" width="104" height="114" fill="transparent" />
        <path d={sparkle(530, 96, 9)} class="shine fill-amber-200" />
        <path d={sparkle(632, 108, 7)} class="shine fill-white" />
        <g class="star-body">
            <path d={star} class="fill-amber-400" />
            {@render eyes(580, 146, 13, 8, -2, 0, -0.5)}
            {@render smile(580, 162, 7)}
        </g>
    </g>

    <g class="pip">
        <rect x="700" y="48" width="120" height="138" fill="transparent" />
        <g class="balloon">
            <path d="M766 140 Q790 124 790 100" class="fill-none stroke-emerald-400" stroke-width="8" stroke-linecap="round" />
            <g transform="translate(766 52) rotate(-20 24 24) scale(2)">
                <MaterialSymbolsLinkRounded style="width: 24px; height: 24px" class="text-gray-100" />
            </g>
            <circle cx="790" cy="96" r="8" class="fill-emerald-400" />
        </g>
        {@render legs(740, 162, 12, "fill-emerald-400")}
        <path d={pip} class="fill-emerald-400" />
        {@render eyes(740, 133, 11, 7, 1, -1, -4)}
        {@render smile(740, 147, 6)}
        {@render blush(740, 145, 20)}
    </g>

    <g class="guard">
        <rect x="860" y="112" width="90" height="80" fill="transparent" />
        {@render legs(900, 174, 12, "fill-red-400")}
        <path d={guard} class="fill-red-400" />
        {@render eyes(896, 145, 11, 7, -1, 1, -2.5)}
        <path d="M878 132 l11 4 M914 132 l-11 4" class="stroke-gray-950" stroke-width="4" stroke-linecap="round" />
        <g class="shield">
            <g transform="translate(914 150) scale(1.25)">
                <MaterialSymbolsShieldRounded style="width: 24px; height: 24px" class="text-gray-100" />
            </g>
        </g>
    </g>
</svg>

<style>
    .blink {
        transform-box: fill-box;
        transform-origin: center;
        animation: blink 6s infinite paused;
    }
    svg[data-awake] .blink {
        animation-play-state: running;
    }

    .note {
        opacity: 0;
        transform: translateY(12px);
        transition:
            opacity 150ms ease-in,
            transform 150ms ease-in;
    }
    .beat:hover .note {
        opacity: 1;
        transform: none;
        transition:
            opacity 200ms ease-out,
            transform 400ms var(--ease-spring);
    }
    .beat-head {
        transform-box: view-box;
        transform-origin: 100px 162px;
    }
    .beat:hover .beat-head {
        animation: bop 700ms ease-in-out;
    }

    .peek-head {
        transition: transform 500ms var(--ease-spring);
    }
    .peek-hands {
        transition: opacity 200ms ease-out;
    }
    .peek:hover .peek-head,
    svg:has(.peek-hands:hover) .peek-head {
        transform: translateY(112px);
        transition: transform 250ms ease-in;
    }
    svg:has(.peek:hover, .peek-hands:hover) .peek-hands {
        opacity: 0;
        transition: opacity 150ms ease-in 100ms;
    }

    .dash:hover .dash-body {
        animation: hop 500ms ease-in-out;
    }

    .star-body {
        transform-box: view-box;
        transform-origin: 580px 174px;
        transition: transform 300ms ease-out;
    }
    .star:hover .star-body {
        transform: scale(1.12);
        transition: transform 400ms var(--ease-spring);
    }
    .shine {
        transform-box: fill-box;
        transform-origin: center;
        opacity: 0;
        transform: scale(0);
        transition:
            opacity 150ms ease-in,
            transform 150ms ease-in;
    }
    .star:hover .shine {
        opacity: 1;
        transform: none;
        transition:
            opacity 200ms ease-out,
            transform 400ms var(--ease-spring);
    }

    .balloon {
        transform-box: view-box;
        transform-origin: 766px 140px;
        transition: transform 500ms var(--ease-spring);
    }
    .pip:hover .balloon {
        transform: rotate(-16deg);
    }

    .shield {
        transform-box: fill-box;
        transform-origin: center;
        transition: transform 400ms var(--ease-spring);
    }
    .guard:hover .shield {
        transform: translate(-32px, -24px) scale(1.3);
    }

    @keyframes blink {
        0%,
        95%,
        100% {
            transform: none;
        }
        97% {
            transform: scaleY(0.1);
        }
    }
    @keyframes bop {
        25% {
            transform: rotate(-8deg);
        }
        75% {
            transform: rotate(8deg);
        }
    }
    @keyframes hop {
        40% {
            transform: translateY(-28px);
        }
    }
</style>
