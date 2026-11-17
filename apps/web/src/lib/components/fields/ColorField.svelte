<script module lang="ts">
    export const SWATCHES = [
        { name: "Square", value: "#1FCEEC" },
        { name: "Blurple", value: "#5865F2" },
        { name: "Green", value: "#57F287" },
        { name: "Yellow", value: "#FEE75C" },
        { name: "Orange", value: "#E67E22" },
        { name: "Red", value: "#ED4245" },
        { name: "Fuchsia", value: "#EB459E" },
        { name: "Purple", value: "#9B59B6" },
    ];
</script>

<script lang="ts">
    import Popup from "#lib/components/ui/Popup.svelte";
    import { field, focusRing } from "#lib/components/ui/styles.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { ColorPicker, parseColor } from "@ark-ui/svelte/color-picker";
    import MaterialSymbolsBlockRounded from "~icons/material-symbols/block-rounded";
    import MaterialSymbolsCheckRounded from "~icons/material-symbols/check-rounded";
    import MaterialSymbolsColorizeRounded from "~icons/material-symbols/colorize-rounded";

    let { value = $bindable(null), label = "Color" }: { value?: string | null; label?: string } = $props();

    let open = $state(false);
    const normal = (hex: string | null) => hex?.toUpperCase() ?? null;
    const current = $derived(normal(value));
    const custom = $derived(current !== null && !SWATCHES.some((swatch) => swatch.value === current));
    const color = $derived(parseColor(current ?? SWATCHES[0]!.value));

    const swatch = [
        "ripple flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-2xl transition-transform hover:scale-110 md:size-8 md:rounded-xl [&>svg]:size-5",
        focusRing,
    ];
    const thumb =
        "size-5 rounded-full border-2 border-white shadow-md shadow-black/50 outline-none focus-visible:ring-4 focus-visible:ring-accent/60";
</script>

<div class="flex flex-wrap items-center gap-2">
    <Tooltip content="No color">
        <button
            type="button"
            aria-pressed={current === null}
            class={[swatch, "bg-gray-700 text-gray-300 aria-pressed:bg-accent/20 aria-pressed:text-accent"]}
            onclick={() => (value = null)}
        >
            <MaterialSymbolsBlockRounded />
        </button>
    </Tooltip>
    {#each SWATCHES as entry (entry.value)}
        <Tooltip lazy content={entry.name}>
            <button
                type="button"
                aria-pressed={current === entry.value}
                style:background-color={entry.value}
                class={[swatch, "text-gray-950"]}
                onclick={() => (value = entry.value)}
            >
                {#if current === entry.value}<MaterialSymbolsCheckRounded />{:else}<span class="sr-only">{entry.name}</span>{/if}
            </button>
        </Tooltip>
    {/each}

    <Popup
        bind:open
        title="Custom color"
        placement="bottom-start"
        contentClass="w-72"
        triggerClass={[field, "h-10! w-40! cursor-pointer bg-gray-700! pl-1 text-left hover:bg-gray-600! md:h-8! md:pl-1"]}
    >
        {#snippet trigger()}
            <span
                class={["size-8 shrink-0 rounded-xl md:size-6 md:rounded-lg", !custom && "border-2 border-dashed border-gray-500"]}
                style:background-color={custom ? current : undefined}
            ></span>
            <span class={["min-w-0 flex-1 truncate", custom ? "font-mono" : "text-gray-400"]}>{custom ? current : "Custom"}</span>
            <MaterialSymbolsColorizeRounded />
        {/snippet}

        <ColorPicker.Root
            inline
            format="hsba"
            value={color}
            onValueChange={(details) => (value = normal(details.value.toString("hex")))}
            class="flex flex-col gap-4 p-2 md:p-0"
        >
            <ColorPicker.Area class="relative h-40 w-full touch-none">
                <ColorPicker.AreaBackground class="size-full rounded-2xl" />
                <ColorPicker.AreaThumb class={thumb} />
            </ColorPicker.Area>
            <ColorPicker.ChannelSlider channel="hue" class="relative mx-2.5 h-5 touch-none">
                <ColorPicker.ChannelSliderTrack class="top-1 -mx-2.5 h-3 rounded-full" />
                <ColorPicker.ChannelSliderThumb class={[thumb, "-translate-x-1/2 -translate-y-1/2"]} />
            </ColorPicker.ChannelSlider>
            <div class="flex items-center gap-2">
                <Tooltip content="Pick from the screen">
                    <ColorPicker.EyeDropperTrigger
                        class={[
                            "ripple flex size-12 shrink-0 cursor-pointer items-center justify-center rounded-control-lg bg-gray-700 text-gray-100 hover:bg-gray-600 md:size-10 md:rounded-2xl [&>svg]:size-5",
                            focusRing,
                        ]}
                    >
                        <MaterialSymbolsColorizeRounded />
                    </ColorPicker.EyeDropperTrigger>
                </Tooltip>
                <label class={[field, "flex-1 bg-gray-700 pl-2 hover:bg-gray-600"]}>
                    <ColorPicker.ValueSwatch class="size-8 shrink-0 rounded-xl md:size-6 md:rounded-lg" />
                    <ColorPicker.ChannelInput
                        channel="hex"
                        aria-label="{label} hex"
                        class="w-full min-w-0 bg-transparent font-mono uppercase outline-none"
                    />
                </label>
            </div>
            <ColorPicker.HiddenInput />
        </ColorPicker.Root>
    </Popup>
</div>
