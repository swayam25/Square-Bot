<script lang="ts">
    import Portal from "#lib/components/ui/Portal.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { Dialog } from "@ark-ui/svelte/dialog";
    import MaterialSymbolsChevronLeftRounded from "~icons/material-symbols/chevron-left-rounded";
    import MaterialSymbolsChevronRightRounded from "~icons/material-symbols/chevron-right-rounded";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";
    import MaterialSymbolsOpenInNewRounded from "~icons/material-symbols/open-in-new-rounded";

    let { src = $bindable(null) }: { src?: string | null } = $props();

    let all = $state<string[]>([]);
    $effect(() => {
        if (src) all = [...new Set([...document.querySelectorAll<HTMLImageElement>("img[data-discord-image]")].map((image) => image.src))];
    });
    const index = $derived(src ? all.indexOf(src) : -1);
    const many = $derived(index !== -1 && all.length > 1);

    function step(by: number) {
        if (many) src = all[(index + by + all.length) % all.length];
    }

    function keys(event: KeyboardEvent) {
        if (event.key === "ArrowLeft") step(-1);
        else if (event.key === "ArrowRight") step(1);
    }

    const tool = "flex size-10 cursor-pointer items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20 [&_svg]:size-5";
</script>

<Dialog.Root open={src !== null} onOpenChange={(details) => !details.open && (src = null)} lazyMount unmountOnExit>
    <Portal>
        <Dialog.Backdrop class="fixed inset-0 z-100 bg-black/85 data-[state=closed]:animate-fade-out data-[state=open]:animate-fade-in" />
        <Dialog.Positioner class="fixed inset-0 z-100">
            <Dialog.Content
                aria-label="Picture"
                class="flex size-full flex-col outline-none data-[state=closed]:animate-fade-out data-[state=open]:animate-fade-in"
                onkeydown={keys}
            >
                <div class="flex items-center justify-end gap-2 p-4">
                    {#if many}<span class="mr-auto font-mono text-sm text-white/70">{index + 1} / {all.length}</span>{/if}
                    {#if src}
                        <Tooltip content="Open in a new tab" placement="bottom">
                            <a href={src} target="_blank" rel="noopener noreferrer" class={tool}>
                                <MaterialSymbolsOpenInNewRounded />
                            </a>
                        </Tooltip>
                    {/if}
                    <Tooltip content="Close" placement="bottom"
                        ><Dialog.CloseTrigger class={tool}><MaterialSymbolsCloseRounded /></Dialog.CloseTrigger></Tooltip
                    >
                </div>
                <div
                    role="presentation"
                    class="flex min-h-0 flex-1 items-center justify-center gap-4 px-4 pb-6"
                    onclick={(event) => event.target === event.currentTarget && (src = null)}
                >
                    {#if many}
                        <Tooltip content="Previous picture" class="shrink-0">
                            <button type="button" class={tool} onclick={() => step(-1)}>
                                <MaterialSymbolsChevronLeftRounded />
                            </button>
                        </Tooltip>
                    {/if}
                    {#if src}
                        <img {src} alt="" class="max-h-full min-w-0 rounded-lg object-contain" />
                    {/if}
                    {#if many}
                        <Tooltip content="Next picture" class="shrink-0">
                            <button type="button" class={tool} onclick={() => step(1)}>
                                <MaterialSymbolsChevronRightRounded />
                            </button>
                        </Tooltip>
                    {/if}
                </div>
            </Dialog.Content>
        </Dialog.Positioner>
    </Portal>
</Dialog.Root>
