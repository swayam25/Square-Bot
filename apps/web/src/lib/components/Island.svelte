<script lang="ts">
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import { mobile } from "#lib/media.ts";
    import { overlays } from "#lib/overlays.svelte.ts";
    import { toasts, type Toast, type Tone } from "#lib/toast.svelte.ts";
    import type { Component } from "svelte";
    import { blur } from "svelte/transition";
    import MaterialSymbolsCheckCircleRounded from "~icons/material-symbols/check-circle-rounded";
    import MaterialSymbolsErrorRounded from "~icons/material-symbols/error-rounded";
    import MaterialSymbolsInfoRounded from "~icons/material-symbols/info-rounded";
    import MaterialSymbolsWarningRounded from "~icons/material-symbols/warning-rounded";
    import SvgSpinners90RingWithBg from "~icons/svg-spinners/90-ring-with-bg";

    let { docked = false }: { docked?: boolean } = $props();

    const tones: Record<Tone, { icon: Component; class: string }> = {
        success: { icon: MaterialSymbolsCheckCircleRounded, class: "bg-emerald-400/10 text-emerald-400" },
        info: { icon: MaterialSymbolsInfoRounded, class: "bg-accent/10 text-accent" },
        warning: { icon: MaterialSymbolsWarningRounded, class: "bg-amber-400/10 text-amber-400" },
        error: { icon: MaterialSymbolsErrorRounded, class: "bg-red-400/10 text-red-400" },
        loading: { icon: SvgSpinners90RingWithBg, class: "bg-surface-2 text-gray-400" },
    };

    let held = $state<Toast | null>(null);
    $effect(() => {
        if (toasts.current) held = toasts.current;
    });
    const item = $derived(toasts.current ?? held);
    const open = $derived(toasts.current !== null);

    let track = $state(0);
    let width = $state(0);
    let height = $state(0);

    // A docked island is a bulge of the content frame, so over a scrim it would show as a stray shape: it floats free instead
    const attached = $derived(docked && overlays.open === 0);
    // An open drawer owns the bottom of a phone screen
    const top = $derived(!attached && mobile.current && overlays.open > 0);
    const shape = $derived(attached ? (mobile.current ? "rounded-t-3xl" : "rounded-tl-3xl") : "rounded-3xl");

    const motion = $derived(
        open
            ? "width 550ms var(--ease-spring), height 650ms var(--ease-spring)"
            : "width 350ms var(--ease-smooth) 80ms, height 300ms var(--ease-smooth) 80ms",
    );
</script>

<!-- Above drawers and dialogs (z-50+), which portal to the body: a result that lands while one is open still shows -->
<div
    bind:clientWidth={track}
    class={[
        "pointer-events-none z-60 flex",
        mobile.current ? "justify-center" : "justify-end",
        attached
            ? ["absolute bottom-0", mobile.current ? "inset-x-12" : "right-0"]
            : ["fixed", mobile.current ? ["inset-x-4", top ? "top-4" : "bottom-4"] : "right-6 bottom-6"],
    ]}
>
    <div
        role="status"
        aria-live="polite"
        inert={!open}
        style:width="{open ? width : 0}px"
        style:height="{open ? height : 0}px"
        style:transition={motion}
        style:--fillet={open ? "1.5rem" : "0px"}
        class={["relative shrink-0 bg-surface-1", shape, !attached && "shadow-2xl shadow-black/50", open && "pointer-events-auto"]}
    >
        {#if attached}
            {#if mobile.current}
                <span aria-hidden="true" class="fillet fillet-flip absolute bottom-0 left-full" style:transition={motion}></span>
            {:else}
                <span aria-hidden="true" class="fillet absolute right-0 bottom-full" style:transition={motion}></span>
            {/if}
            <span aria-hidden="true" class="fillet absolute right-full bottom-0" style:transition={motion}></span>
        {/if}

        <div class={["absolute inset-0 overflow-hidden", shape]}>
            <!-- Pinned to the island's edge, so the growing shape uncovers the toast instead of dragging it along -->
            <div
                bind:clientWidth={width}
                bind:clientHeight={height}
                style:width={mobile.current ? `${track}px` : undefined}
                class={[
                    "absolute transition-[opacity,scale,filter]",
                    top ? "top-0" : "bottom-0",
                    mobile.current
                        ? top
                            ? "left-1/2 origin-top -translate-x-1/2"
                            : "left-1/2 origin-bottom -translate-x-1/2"
                        : "right-0 w-max max-w-88 origin-bottom-right",
                    open ? "scale-100 opacity-100 blur-[0px] delay-150 duration-300" : "scale-95 opacity-0 blur-sm duration-150",
                ]}
            >
                {#if item}
                    {@const tone = tones[item.tone]}
                    {#key item.id}
                        <button
                            type="button"
                            aria-label={item.tone === "loading" ? undefined : `Dismiss: ${item.message}`}
                            disabled={item.tone === "loading"}
                            class="flex w-full items-center gap-4 p-4 pr-6 text-left disabled:cursor-default"
                            onclick={() => toasts.dismiss(item.id)}
                            in:blur={{ amount: 6, duration: 300, delay: 100 }}
                        >
                            {#if item.person}
                                <Avatar src={item.person.avatarUrl} name={item.person.name} class="size-10" />
                            {:else}
                                <span class={["flex size-10 shrink-0 items-center justify-center rounded-full", tone.class]}>
                                    <tone.icon class="size-5" />
                                </span>
                            {/if}
                            <span class="flex min-w-0 flex-col">
                                <span class="line-clamp-4 text-sm font-semibold wrap-break-word">{item.message}</span>
                                {#if item.description}<span class="line-clamp-4 text-xs wrap-break-word text-gray-400">{item.description}</span>{/if}
                            </span>
                        </button>
                    {/key}
                {/if}
            </div>
        </div>
    </div>
</div>

<style>
    .fillet {
        width: var(--fillet);
        height: var(--fillet);
        background: radial-gradient(circle farthest-side at 0 0, transparent 98%, var(--color-surface-1) 100%);
    }

    .fillet-flip {
        background: radial-gradient(circle farthest-side at 100% 0, transparent 98%, var(--color-surface-1) 100%);
    }
</style>
