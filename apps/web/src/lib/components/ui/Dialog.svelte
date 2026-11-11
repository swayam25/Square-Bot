<script lang="ts">
    import Drawer from "#lib/components/ui/Drawer.svelte";
    import { mobile } from "#lib/media.ts";
    import { Dialog } from "@ark-ui/svelte/dialog";
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

{#if mobile.current}
    <Drawer bind:open {title} {description} {trigger} {triggerClass} {children} {footer} />
{:else}
    <Dialog.Root bind:open>
        {#if trigger}
            <Dialog.Trigger class={triggerClass}>{@render trigger()}</Dialog.Trigger>
        {/if}
        <Portal>
            <Dialog.Backdrop class="fixed inset-0 z-50 bg-mist-950/60 data-[state=closed]:animate-fade-out data-[state=open]:animate-fade-in" />
            <Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-6">
                <Dialog.Content
                    class="flex max-h-full w-full max-w-lg flex-col gap-6 rounded-4xl bg-surface-1 p-6 shadow-2xl shadow-black/50 outline-none data-[state=closed]:animate-pop-out data-[state=open]:animate-pop-in"
                >
                    <div class="flex flex-col gap-1">
                        <Dialog.Title class="font-display text-xl font-semibold">{title}</Dialog.Title>
                        {#if description}
                            <Dialog.Description class="text-sm text-mist-400">{description}</Dialog.Description>
                        {/if}
                    </div>
                    <div class="min-h-0 overflow-y-auto">{@render children()}</div>
                    {#if footer}
                        <div class="flex justify-end gap-2">{@render footer()}</div>
                    {/if}
                </Dialog.Content>
            </Dialog.Positioner>
        </Portal>
    </Dialog.Root>
{/if}
