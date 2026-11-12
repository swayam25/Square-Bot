<script lang="ts">
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import { mobile } from "#lib/media.ts";
    import { toasts, type Toast, type Tone } from "#lib/toast.svelte.ts";
    import type { Component } from "svelte";
    import { fly } from "svelte/transition";
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
        loading: { icon: SvgSpinners90RingWithBg, class: "bg-surface-2 text-mist-400" },
    };

    let held = $state<Toast | null>(null);
    $effect(() => {
        if (toasts.current) held = toasts.current;
    });
    const item = $derived(toasts.current ?? held);
    const open = $derived(toasts.current !== null);

    let width = $state(0);
    let height = $state(0);

    const wide = $derived(docked && !mobile.current);
    const fillet = $derived(open ? "1.5rem" : "0px");
</script>

<!-- Above drawers and dialogs (z-50), which portal to the body: a result that lands while one is open still shows -->
<div
    class={[
        "pointer-events-none z-60 flex justify-end",
        docked ? "absolute inset-x-12 bottom-0 md:inset-x-auto md:right-0" : "fixed inset-x-4 bottom-4 md:inset-x-auto md:right-6 md:bottom-6",
    ]}
>
    <div
        role="status"
        aria-live="polite"
        inert={!open}
        style:width={wide || !mobile.current ? `${width}px` : undefined}
        style:height="{open ? height : 0}px"
        style:--fillet={fillet}
        class={[
            "relative bg-surface-1 transition-[width,height] duration-500 ease-spring",
            mobile.current && "w-full",
            !docked && "overflow-hidden rounded-3xl shadow-2xl shadow-black/50",
            docked && (wide ? "rounded-tl-3xl" : "rounded-t-3xl"),
            open && "pointer-events-auto",
        ]}
    >
        {#if docked}
            {#if wide}
                <span aria-hidden="true" class="fillet absolute right-0 bottom-full"></span>
            {:else}
                <span aria-hidden="true" class="fillet fillet-flip absolute bottom-0 left-full"></span>
            {/if}
            <span aria-hidden="true" class="fillet absolute right-full bottom-0"></span>
        {/if}

        <div class={["absolute inset-0 overflow-hidden", docked && (wide ? "rounded-tl-3xl" : "rounded-t-3xl")]}>
            <div bind:clientWidth={width} bind:clientHeight={height} class={["absolute top-0 right-0", mobile.current ? "left-0" : "w-max max-w-88"]}>
                {#if item}
                    {@const tone = tones[item.tone]}
                    {#key item.id}
                        <button
                            type="button"
                            aria-label={item.tone === "loading" ? undefined : `Dismiss: ${item.message}`}
                            disabled={item.tone === "loading"}
                            class="flex w-full items-center gap-4 p-4 pr-6 text-left disabled:cursor-default"
                            onclick={() => toasts.dismiss(item.id)}
                            in:fly={{ y: 12, duration: 300, delay: 100 }}
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
                                {#if item.description}<span class="line-clamp-4 text-xs wrap-break-word text-mist-400">{item.description}</span>{/if}
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
        transition:
            width 500ms var(--ease-spring),
            height 500ms var(--ease-spring);
    }

    .fillet-flip {
        background: radial-gradient(circle farthest-side at 100% 0, transparent 98%, var(--color-surface-1) 100%);
    }
</style>
