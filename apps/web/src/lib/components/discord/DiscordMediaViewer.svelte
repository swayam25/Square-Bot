<script lang="ts">
    import square from "#lib/assets/square.svg";
    import DiscordTooltip from "#lib/components/discord/DiscordTooltip.svelte";
    import DiscordVideo from "#lib/components/discord/DiscordVideo.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Portal from "#lib/components/ui/Portal.svelte";
    import type { Viewing } from "#lib/discord/context.ts";
    import { Dialog } from "@ark-ui/svelte/dialog";
    import MaterialSymbolsArrowBackRounded from "~icons/material-symbols/arrow-back-rounded";
    import MaterialSymbolsArrowForwardRounded from "~icons/material-symbols/arrow-forward-rounded";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";
    import MaterialSymbolsDownloadRounded from "~icons/material-symbols/download-rounded";
    import MaterialSymbolsOpenInNewRounded from "~icons/material-symbols/open-in-new-rounded";
    import MaterialSymbolsPlayArrowRounded from "~icons/material-symbols/play-arrow-rounded";
    import MaterialSymbolsZoomInRounded from "~icons/material-symbols/zoom-in-rounded";
    import MaterialSymbolsZoomOutRounded from "~icons/material-symbols/zoom-out-rounded";

    let { viewing = $bindable(null) }: { viewing?: Viewing | null } = $props();

    let zoomed = $state(false);
    let origin = $state("50% 50%");

    const media = $derived(viewing?.media ?? []);
    const current = $derived(viewing ? media[viewing.index] : undefined);
    const many = $derived(media.length > 1);

    function show(index: number) {
        if (!viewing) return;
        viewing = { ...viewing, index: (index + media.length) % media.length };
        zoomed = false;
    }

    const KEEP_OPEN = "button, a, img, video, [role=slider], [role=group]";

    function keys(event: KeyboardEvent) {
        if (!viewing || !many) return;
        if (event.key === "ArrowLeft") show(viewing.index - 1);
        else if (event.key === "ArrowRight") show(viewing.index + 1);
    }

    function aim(event: MouseEvent) {
        const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
        origin = `${((event.clientX - box.left) / box.width) * 100}% ${((event.clientY - box.top) / box.height) * 100}%`;
    }

    const tool =
        "flex size-8 cursor-pointer items-center justify-center rounded-md text-dc-icon transition-colors hover:bg-dc-hover hover:text-dc-strong [&_svg]:size-5";
    const panel = "rounded-lg border border-dc-border bg-dc-bg shadow-lg shadow-black/40";
</script>

<Dialog.Root
    open={viewing !== null}
    onOpenChange={(details) => {
        if (!details.open) {
            viewing = null;
            zoomed = false;
        }
    }}
    lazyMount
    unmountOnExit
>
    <Portal>
        <Dialog.Backdrop class="fixed inset-0 z-100 bg-black/90 data-[state=closed]:animate-fade-out data-[state=open]:animate-fade-in" />
        <Dialog.Positioner class="fixed inset-0 z-100">
            <Dialog.Content
                aria-label={current?.name || "Media"}
                class="relative size-full text-dc-text outline-none data-[state=closed]:animate-fade-out data-[state=open]:animate-fade-in"
                onkeydown={keys}
                onclick={(event) => !(event.target as Element).closest(KEEP_OPEN) && (viewing = null)}
            >
                <div class={["absolute inset-x-4 top-20 flex items-center justify-center md:inset-x-24", many ? "bottom-20" : "bottom-6"]}>
                    {#if current?.kind === "image"}
                        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
                        <img
                            src={current.src}
                            alt={current.name ?? ""}
                            width={current.width}
                            height={current.height}
                            style:transform-origin={origin}
                            class={[
                                "max-h-full max-w-full object-contain transition-transform duration-300 ease-out",
                                zoomed ? "scale-200 cursor-zoom-out" : "cursor-zoom-in",
                            ]}
                            onpointermove={(event) => zoomed && aim(event)}
                            onclick={(event) => {
                                aim(event);
                                zoomed = !zoomed;
                            }}
                        />
                    {:else if current?.kind === "video"}
                        {#key current.src}
                            <DiscordVideo src={current.src} width={current.width} height={current.height} class="max-h-full max-w-full" />
                        {/key}
                    {:else if current?.kind === "gif"}
                        <video src={current.src} autoplay loop muted playsinline class="max-h-full max-w-full rounded-lg"></video>
                    {/if}
                </div>

                {#if viewing?.author}
                    {@const author = viewing.author}
                    <div class="absolute top-6 left-6 flex min-w-0 items-center gap-3">
                        {#if author.avatar === undefined}
                            <span class="flex size-8 shrink-0 items-center justify-center rounded-full bg-gray-950">
                                <img src={square} alt="" class="size-6" />
                            </span>
                        {:else}
                            <Avatar src={author.avatar} name={author.name} class="size-8 shrink-0" />
                        {/if}
                        <div class="flex min-w-0 flex-col">
                            <span class="truncate text-sm leading-4.5 font-semibold text-dc-strong">{author.name}</span>
                            <span class="text-xs text-dc-muted">{author.time}</span>
                        </div>
                    </div>
                {/if}

                <div class="absolute top-6 right-6 flex items-center gap-3">
                    <div class={["flex items-center gap-1 p-1", panel]}>
                        {#if current?.kind === "image"}
                            <DiscordTooltip content={zoomed ? "Zoom Out" : "Zoom In"} placement="bottom">
                                <button
                                    type="button"
                                    class={tool}
                                    onclick={() => {
                                        origin = "50% 50%";
                                        zoomed = !zoomed;
                                    }}
                                >
                                    {#if zoomed}<MaterialSymbolsZoomOutRounded />{:else}<MaterialSymbolsZoomInRounded />{/if}
                                </button>
                            </DiscordTooltip>
                        {/if}
                        {#if current}
                            <DiscordTooltip content="Open in Browser" placement="bottom">
                                <a href={current.src} target="_blank" rel="noopener noreferrer" class={tool}><MaterialSymbolsOpenInNewRounded /></a>
                            </DiscordTooltip>
                            <DiscordTooltip content="Download" placement="bottom">
                                <a href={current.src} download={current.name || ""} target="_blank" rel="noopener noreferrer" class={tool}>
                                    <MaterialSymbolsDownloadRounded />
                                </a>
                            </DiscordTooltip>
                        {/if}
                    </div>
                    <DiscordTooltip content="Close" placement="bottom">
                        <button
                            type="button"
                            class={["flex size-10 cursor-pointer items-center justify-center", panel, tool]}
                            onclick={() => (viewing = null)}
                        >
                            <MaterialSymbolsCloseRounded />
                        </button>
                    </DiscordTooltip>
                </div>

                {#if many && viewing}
                    {@const at = viewing.index}
                    <DiscordTooltip content="Previous" class="absolute top-1/2 left-6 -translate-y-1/2">
                        <button
                            type="button"
                            class={["flex size-10 cursor-pointer items-center justify-center", panel, tool]}
                            onclick={() => show(at - 1)}
                        >
                            <MaterialSymbolsArrowBackRounded />
                        </button>
                    </DiscordTooltip>
                    <DiscordTooltip content="Next" class="absolute top-1/2 right-6 -translate-y-1/2">
                        <button
                            type="button"
                            class={["flex size-10 cursor-pointer items-center justify-center", panel, tool]}
                            onclick={() => show(at + 1)}
                        >
                            <MaterialSymbolsArrowForwardRounded />
                        </button>
                    </DiscordTooltip>

                    <div class="absolute inset-x-0 bottom-6 flex justify-center">
                        <div class="flex max-w-[calc(100%-3rem)] gap-2 overflow-x-auto p-1">
                            {#each media as item, index (index)}
                                <button
                                    type="button"
                                    aria-current={index === at || undefined}
                                    class={[
                                        "relative size-10 shrink-0 cursor-pointer overflow-hidden rounded-md bg-dc-surface transition-opacity",
                                        index === at ? "opacity-100 ring-2 ring-white" : "opacity-50 hover:opacity-100",
                                    ]}
                                    onclick={() => show(index)}
                                >
                                    {#if item.kind === "image"}
                                        <img src={item.src} alt={item.name || `Picture ${index + 1}`} loading="lazy" class="size-full object-cover" />
                                    {:else}
                                        <video src={item.src} preload="metadata" muted playsinline class="size-full object-cover"></video>
                                        <span class="absolute inset-0 flex items-center justify-center text-white">
                                            <MaterialSymbolsPlayArrowRounded class="size-4 drop-shadow" />
                                        </span>
                                        <span class="sr-only">{item.name || `Video ${index + 1}`}</span>
                                    {/if}
                                </button>
                            {/each}
                        </div>
                    </div>
                {/if}
            </Dialog.Content>
        </Dialog.Positioner>
    </Portal>
</Dialog.Root>
