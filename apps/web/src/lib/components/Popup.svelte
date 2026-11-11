<script lang="ts">
    import Drawer from "#lib/components/Drawer.svelte";
    import { mobile } from "#lib/media.ts";
    import { Popover } from "@ark-ui/svelte/popover";
    import { Portal } from "@ark-ui/svelte/portal";
    import type { Snippet } from "svelte";
    import type { ClassValue } from "svelte/elements";

    type Placement = "bottom-start" | "bottom-end" | "top-start" | "top-end" | "bottom" | "top" | "left" | "right";

    let {
        open = $bindable(false),
        title,
        trigger,
        triggerClass,
        placement = "bottom-end",
        children,
    }: {
        open?: boolean;
        title: string;
        trigger: Snippet;
        triggerClass?: ClassValue;
        placement?: Placement;
        children: Snippet;
    } = $props();
</script>

{#if mobile.current}
    <Drawer bind:open {title} {trigger} {triggerClass} {children} />
{:else}
    <Popover.Root bind:open positioning={{ placement, gutter: 8 }}>
        <Popover.Trigger class={triggerClass}>{@render trigger()}</Popover.Trigger>
        <Portal>
            <Popover.Positioner class="z-50">
                <Popover.Content
                    aria-label={title}
                    class="w-72 origin-(--transform-origin) rounded-2xl bg-surface-1 p-2 shadow-2xl shadow-black/50 outline-none data-[state=closed]:animate-pop-out data-[state=open]:animate-pop-in"
                >
                    {@render children()}
                </Popover.Content>
            </Popover.Positioner>
        </Portal>
    </Popover.Root>
{/if}
