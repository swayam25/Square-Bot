<script lang="ts">
    import { Drawer } from "@ark-ui/svelte/drawer";
    import { Portal } from "@ark-ui/svelte/portal";
    import type { Snippet } from "svelte";
    import type { ClassValue } from "svelte/elements";

    let {
        open = $bindable(false),
        title,
        description,
        trigger,
        triggerClass,
        children,
        footer,
    }: {
        open?: boolean;
        title: string;
        description?: string;
        trigger?: Snippet;
        triggerClass?: ClassValue;
        children: Snippet;
        footer?: Snippet;
    } = $props();
</script>

<Drawer.Root bind:open>
    {#if trigger}
        <Drawer.Trigger class={triggerClass}>{@render trigger()}</Drawer.Trigger>
    {/if}
    <Portal>
        <Drawer.Backdrop class="fixed inset-0 z-50 bg-mist-950/60 data-[state=closed]:animate-fade-out data-[state=open]:animate-fade-in" />
        <Drawer.Positioner class="fixed inset-x-0 bottom-0 z-50">
            <!-- The `after:` strip fills the gap under the sheet when it's pulled past its height -->
            <Drawer.Content
                class="relative flex max-h-[calc(100dvh-4rem)] flex-col rounded-t-[28px] bg-surface-1 pb-[env(safe-area-inset-bottom)] shadow-2xl shadow-black/50 outline-none after:absolute after:inset-x-0 after:top-full after:h-dvh after:bg-surface-1 data-[state=closed]:animate-slide-down data-[state=open]:animate-slide-up"
            >
                <Drawer.Grabber class="flex justify-center py-4">
                    <Drawer.GrabberIndicator class="h-1 w-12 rounded-full bg-white/20" />
                </Drawer.Grabber>
                <div class="flex flex-col gap-1 px-6 pb-4">
                    <Drawer.Title class="font-display text-xl font-semibold">{title}</Drawer.Title>
                    {#if description}
                        <Drawer.Description class="text-sm text-mist-400">{description}</Drawer.Description>
                    {/if}
                </div>
                <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 pb-6">{@render children()}</div>
                {#if footer}
                    <div class="flex flex-col-reverse gap-2 px-6 pb-6">{@render footer()}</div>
                {/if}
            </Drawer.Content>
        </Drawer.Positioner>
    </Portal>
</Drawer.Root>
