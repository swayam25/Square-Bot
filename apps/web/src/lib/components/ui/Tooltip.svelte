<script lang="ts">
    import Portal from "#lib/components/ui/Portal.svelte";
    import { Tooltip } from "@ark-ui/svelte/tooltip";
    import type { Snippet } from "svelte";
    import type { ClassValue } from "svelte/elements";

    let {
        content,
        placement = "top",
        class: className,
        children,
    }: {
        content: string | null | undefined;
        placement?: "top" | "bottom" | "left" | "right";
        class?: ClassValue;
        children: Snippet;
    } = $props();
</script>

<Tooltip.Root disabled={!content} openDelay={300} closeDelay={0} positioning={{ placement, gutter: 8 }}>
    <!-- A span, not Ark's button, so the tooltip still opens over a disabled button, which gets no pointer events -->
    <Tooltip.Trigger>
        {#snippet asChild(props)}
            <span {...props()} class={["inline-flex", className]}>{@render children()}</span>
        {/snippet}
    </Tooltip.Trigger>
    <Portal>
        <Tooltip.Positioner class="z-50">
            <Tooltip.Content
                class="max-w-64 origin-(--transform-origin) rounded-xl bg-surface-3 px-4 py-2 text-xs font-medium text-mist-100 shadow-xl shadow-black/50 data-[state=closed]:animate-pop-out data-[state=open]:animate-pop-in"
            >
                {content}
            </Tooltip.Content>
        </Tooltip.Positioner>
    </Portal>
</Tooltip.Root>
