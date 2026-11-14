<script lang="ts">
    import Drawer from "#lib/components/ui/Drawer.svelte";
    import Portal from "#lib/components/ui/Portal.svelte";
    import { mobile } from "#lib/media.ts";
    import { overlays } from "#lib/overlays.svelte.ts";
    import { Dialog } from "@ark-ui/svelte/dialog";
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
        dismissable = true,
    }: {
        open?: boolean;
        title: string;
        description?: string;
        trigger?: Snippet;
        triggerClass?: ClassValue;
        children: Snippet;
        footer?: Snippet;
        dismissable?: boolean;
    } = $props();

    $effect(() => {
        if (open && !mobile.current) return overlays.hold();
    });
</script>

{#if mobile.current}
    <Drawer bind:open {title} {description} {trigger} {triggerClass} {children} {footer} {dismissable} />
{:else}
    <Dialog.Root bind:open closeOnEscape={dismissable} closeOnInteractOutside={dismissable}>
        {#if trigger}
            <Dialog.Trigger class={triggerClass}>{@render trigger()}</Dialog.Trigger>
        {/if}
        <Portal>
            <Dialog.Backdrop class="fixed inset-0 z-50 bg-gray-950/60 data-[state=closed]:animate-fade-out data-[state=open]:animate-fade-in" />
            <Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-6">
                <Dialog.Content
                    class="flex max-h-full w-full max-w-lg flex-col gap-6 rounded-4xl bg-surface-1 p-6 shadow-2xl shadow-black/50 outline-none data-[state=closed]:animate-pop-out data-[state=open]:animate-pop-in"
                >
                    <div class="flex flex-col gap-1">
                        <Dialog.Title class="font-display text-xl font-semibold">{title}</Dialog.Title>
                        {#if description}
                            <Dialog.Description class="text-sm text-gray-400">{description}</Dialog.Description>
                        {/if}
                    </div>
                    <div class="-m-1 min-h-0 overflow-y-auto p-1">{@render children()}</div>
                    {#if footer}
                        <div class="flex justify-end gap-2">{@render footer()}</div>
                    {/if}
                </Dialog.Content>
            </Dialog.Positioner>
        </Portal>
    </Dialog.Root>
{/if}
