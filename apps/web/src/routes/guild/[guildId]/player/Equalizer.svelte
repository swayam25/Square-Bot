<script lang="ts">
    import Button from "#lib/components/ui/Button.svelte";
    import Popup from "#lib/components/ui/Popup.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { mobile } from "#lib/media.ts";
    import { ripple } from "#lib/motion.ts";
    import * as music from "#lib/music.remote.ts";
    import type { EqPreset, PlayerState } from "@square/api-client";
    import type { ClassValue } from "svelte/elements";
    import MaterialSymbolsEqualizerRounded from "~icons/material-symbols/equalizer-rounded";
    import MaterialSymbolsRestartAltRounded from "~icons/material-symbols/restart-alt-rounded";
    import SvgSpinners90RingWithBg from "~icons/svg-spinners/90-ring-with-bg";
    import { control } from "./player.ts";

    let {
        guild,
        player,
        lock = null,
        triggerClass,
    }: { guild: string; player: PlayerState; lock?: string | null; triggerClass?: ClassValue } = $props();

    const presetsQuery = $derived(music.eqPresets(guild));
    const presets = $derived(presetsQuery.current);

    // Presets on one Lavalink filter replace each other, so they're grouped
    const SLOT_TITLES: Record<string, string> = { equalizer: "Tone", timescale: "Speed and pitch" };
    type Group = { title: string; hint: string; presets: EqPreset[] };
    const groups = $derived.by(() => {
        const slots: Record<string, EqPreset[]> = {};
        for (const preset of presets ?? []) (slots[preset.slot] ??= []).push(preset);
        const shared: Group[] = [];
        const free: EqPreset[] = [];
        for (const [slot, list] of Object.entries(slots)) {
            if (list.length > 1) shared.push({ title: SLOT_TITLES[slot] ?? slot, hint: "One at a time", presets: list });
            else free.push(...list);
        }
        return free.length ? [...shared, { title: "Effects", hint: "Mix any", presets: free }] : shared;
    });

    const active = $derived(presets?.filter((preset) => player.eq.includes(preset.name)).map((preset) => preset.label) ?? []);

    let busy = $state<string | null>(null);
    async function run(key: string, action: ReturnType<typeof music.resetEq>) {
        if (busy) return;
        busy = key;
        await control(action);
        busy = null;
    }
    const RESET = "reset";
</script>

{#snippet reset(className?: ClassValue)}
    <Tooltip content={lock ?? (player.eq.length ? null : "Nothing is turned on")} class={className}>
        <Button
            variant="ghost"
            loading={busy === RESET}
            disabled={!!lock || !player.eq.length || (busy !== null && busy !== RESET)}
            class="w-full"
            onclick={() => run(RESET, music.resetEq({ guild }))}
        >
            {#if busy !== RESET}<MaterialSymbolsRestartAltRounded />{/if}Reset
        </Button>
    </Tooltip>
{/snippet}

<Tooltip content={active.length ? `Equalizer: ${active.join(", ")}` : "Equalizer"}>
    <Popup title="Equalizer" placement="top-end" contentClass="w-96" {triggerClass}>
        {#snippet trigger()}
            <MaterialSymbolsEqualizerRounded /><span class="sr-only">Equalizer</span>
        {/snippet}

        <div class="flex flex-col gap-4 md:p-2">
            {#if !mobile.current}
                <div class="flex h-10 items-center justify-between gap-4">
                    <h2 class="font-display text-lg font-semibold">Equalizer</h2>
                    {@render reset()}
                </div>
            {/if}

            {#if presets}
                {#each groups as group (group.title)}
                    <section class="flex flex-col gap-2">
                        <h3 class="flex items-baseline justify-between gap-4 text-xs font-medium text-mist-400">
                            {group.title}<span class="text-2xs font-normal">{group.hint}</span>
                        </h3>
                        <div class="flex flex-wrap gap-2">
                            {#each group.presets as preset (preset.name)}
                                {@const on = player.eq.includes(preset.name)}
                                <Tooltip content={lock ?? preset.description}>
                                    <button
                                        type="button"
                                        aria-pressed={on}
                                        aria-busy={busy === preset.name}
                                        disabled={!!lock || (busy !== null && busy !== preset.name)}
                                        class={[
                                            "ripple relative inline-flex h-10 items-center rounded-full px-4 text-sm font-medium transition-colors disabled:opacity-50",
                                            on ? "bg-accent/20 text-cyan-300 hover:bg-accent/30" : "bg-white/10 text-mist-100 hover:bg-white/15",
                                        ]}
                                        {@attach ripple}
                                        onclick={() => run(preset.name, music.setEq({ guild, preset: preset.name, enabled: !on }))}
                                    >
                                        <span class={[busy === preset.name && "invisible"]}>{preset.label}</span>
                                        {#if busy === preset.name}<SvgSpinners90RingWithBg class="absolute inset-0 m-auto size-4" />{/if}
                                    </button>
                                </Tooltip>
                            {/each}
                        </div>
                    </section>
                {/each}
            {:else if presetsQuery.error}
                <p role="alert" class="text-sm font-medium text-red-400">Square couldn't load the equalizer. Try again in a moment.</p>
            {:else}
                <div aria-hidden="true" class="flex flex-wrap gap-2">
                    {#each [24, 28, 20, 24, 16, 28, 20, 24] as width, i (i)}
                        <span class="h-10 animate-pulse rounded-full bg-white/10" style:width="{width * 0.25}rem"></span>
                    {/each}
                </div>
            {/if}

            {#if mobile.current}{@render reset("w-full")}{/if}
        </div>
    </Popup>
</Tooltip>
