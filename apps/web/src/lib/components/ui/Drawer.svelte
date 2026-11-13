<script module lang="ts">
    // Drawers can open from inside other drawers (a picker in the side panel), so the newest one always stacks on top
    let top = 50;
</script>

<script lang="ts">
    import Portal from "#lib/components/ui/Portal.svelte";
    import { Drawer } from "@ark-ui/svelte/drawer";
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
        plain = false,
        disabled = false,
        class: className,
    }: {
        open?: boolean;
        title: string;
        description?: string;
        trigger?: Snippet;
        triggerClass?: ClassValue;
        children: Snippet;
        footer?: Snippet;
        dismissable?: boolean;
        plain?: boolean;
        disabled?: boolean;
        class?: ClassValue;
    } = $props();

    let content = $state<HTMLElement | null>(null);
    let layer = $state(50);

    $effect.pre(() => {
        if (open) layer = ++top;
    });
</script>

<!-- A plain sheet focuses itself, not its first field, so a phone keyboard doesn't jump up while it slides in -->
<Drawer.Root bind:open closeOnEscape={dismissable} closeOnInteractOutside={dismissable} initialFocusEl={plain ? () => content : undefined}>
    {#if trigger}
        <Drawer.Trigger class={triggerClass} {disabled}>{@render trigger()}</Drawer.Trigger>
    {/if}
    <Portal>
        <Drawer.Backdrop
            style="z-index: {layer}"
            class="fixed inset-0 bg-gray-950/60 data-[state=closed]:animate-fade-out data-[state=open]:animate-fade-in"
        />
        <Drawer.Positioner style="z-index: {layer}" class="fixed inset-x-0 bottom-0">
            <Drawer.Content
                bind:ref={content}
                class={[
                    "relative flex max-h-[calc(100dvh-4rem)] flex-col rounded-t-[28px] bg-surface-1 pb-[env(safe-area-inset-bottom)] shadow-2xl shadow-black/50 outline-none after:absolute after:inset-x-0 after:top-full after:h-dvh after:bg-surface-1 data-[state=closed]:animate-slide-down data-[state=open]:animate-slide-up",
                    className,
                ]}
            >
                <Drawer.Grabber class="flex justify-center py-4">
                    <Drawer.GrabberIndicator class="h-1 w-12 rounded-full bg-white/20" />
                </Drawer.Grabber>
                <div class={plain ? "sr-only" : "flex flex-col gap-1 px-6 pb-3"}>
                    <Drawer.Title class="font-display text-xl font-semibold">{title}</Drawer.Title>
                    {#if description}
                        <Drawer.Description class="text-sm text-gray-400">{description}</Drawer.Description>
                    {/if}
                </div>
                {#if plain}
                    <div class="flex min-h-0 flex-1 flex-col">{@render children()}</div>
                {:else}
                    <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 pt-1 pb-6">{@render children()}</div>
                {/if}
                {#if footer}
                    <div class="flex flex-col-reverse gap-2 px-6 pb-6">{@render footer()}</div>
                {/if}
            </Drawer.Content>
        </Drawer.Positioner>
    </Portal>
</Drawer.Root>
