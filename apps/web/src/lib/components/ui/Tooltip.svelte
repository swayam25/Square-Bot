<script lang="ts">
    import Portal from "#lib/components/ui/Portal.svelte";
    import { Tooltip } from "@ark-ui/svelte/tooltip";
    import type { Snippet } from "svelte";
    import type { Attachment } from "svelte/attachments";
    import type { ClassValue } from "svelte/elements";

    let {
        content,
        placement = "top",
        lazy = false,
        arrow = false,
        class: className,
        contentClass = "max-w-64 rounded-xl bg-gray-700 px-4 py-2 text-xs font-medium text-gray-100 shadow-xl shadow-black/50",
        children,
    }: {
        content: string | null | undefined;
        placement?: "top" | "bottom" | "left" | "right";
        // For plain text in long lists, like a transcript's timestamps: the tooltip is built on first hover, since
        // thousands of them cost seconds to mount. That redraws the content, so never use it around a control
        lazy?: boolean;
        arrow?: boolean;
        class?: ClassValue;
        contentClass?: ClassValue;
        children: Snippet;
    } = $props();

    let armed = $state(false);

    // Frozen once closing starts: a click closes the tooltip and often changes its text, which would flash mid fade
    let open = $state(false);
    let label = $state<string | null | undefined>(null);
    $effect.pre(() => {
        if (open && content) label = content;
    });

    // An icon-only control takes its name from the tooltip, so call sites never set aria-label themselves
    const INTERACTIVE = "button, a[href], input, select, textarea, [role='button'], [tabindex]";
    const named: Attachment<HTMLElement> = (node) => {
        const control = node.querySelector<HTMLElement>(INTERACTIVE);
        if (!control || control.textContent?.trim() || (control.hasAttribute("aria-label") && !control.dataset.tooltipLabel)) return;
        if (content) {
            control.setAttribute("aria-label", content);
            control.dataset.tooltipLabel = "";
        } else {
            control.removeAttribute("aria-label");
            delete control.dataset.tooltipLabel;
        }
    };
</script>

{#if lazy && !armed}
    <span role="presentation" onpointerenter={() => (armed = true)} class={["inline-flex", className]}>{@render children()}</span>
{:else}
    <Tooltip.Root
        lazyMount
        unmountOnExit
        disabled={!content}
        openDelay={300}
        closeDelay={0}
        positioning={{ placement, gutter: 8 }}
        onOpenChange={(details) => (open = details.open)}
    >
        <!-- A span, not Ark's button, so the tooltip still opens over a disabled button, which gets no pointer events -->
        <Tooltip.Trigger>
            {#snippet asChild(props)}
                <span {...props()} {@attach named} class={["inline-flex", className]}>{@render children()}</span>
            {/snippet}
        </Tooltip.Trigger>
        <Portal>
            <Tooltip.Positioner class="z-200">
                <Tooltip.Content
                    class={[
                        "origin-(--transform-origin) wrap-anywhere data-[state=closed]:animate-pop-out data-[state=open]:animate-pop-in",
                        contentClass,
                    ]}
                >
                    {#if arrow}
                        <Tooltip.Arrow class="[--arrow-background:var(--tooltip-bg)] [--arrow-size:10px]">
                            <Tooltip.ArrowTip class="border-t border-l border-(--tooltip-border)" />
                        </Tooltip.Arrow>
                    {/if}
                    {label}
                </Tooltip.Content>
            </Tooltip.Positioner>
        </Portal>
    </Tooltip.Root>
{/if}
