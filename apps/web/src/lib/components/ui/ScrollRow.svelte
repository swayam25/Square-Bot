<script lang="ts">
    import type { Snippet } from "svelte";
    import type { ClassValue, HTMLAttributes } from "svelte/elements";

    let {
        as = "div",
        class: className,
        children,
        ...rest
    }: { as?: "div" | "ul"; class?: ClassValue; children: Snippet } & HTMLAttributes<HTMLElement> = $props();

    let dragging = $state(false);

    // Touch scrolls sideways on its own; a mouse gets grab-to-scroll, and a drag never counts as a click on a chip
    function drag(row: HTMLElement) {
        let startX = 0;
        let startScroll = 0;
        let moved = false;

        function move(event: PointerEvent) {
            const dx = event.clientX - startX;
            if (Math.abs(dx) > 4) moved = true;
            row.scrollLeft = startScroll - dx;
        }
        function up() {
            dragging = false;
            removeEventListener("pointermove", move);
            removeEventListener("pointerup", up);
            removeEventListener("pointercancel", up);
        }
        function down(event: PointerEvent) {
            moved = false;
            if (event.pointerType !== "mouse" || event.button !== 0 || row.scrollWidth <= row.clientWidth) return;
            startX = event.clientX;
            startScroll = row.scrollLeft;
            dragging = true;
            addEventListener("pointermove", move);
            addEventListener("pointerup", up);
            addEventListener("pointercancel", up);
        }
        function click(event: MouseEvent) {
            if (!moved) return;
            moved = false;
            event.preventDefault();
            event.stopPropagation();
        }

        row.addEventListener("pointerdown", down);
        row.addEventListener("click", click, { capture: true });
        return () => {
            up();
            row.removeEventListener("pointerdown", down);
            row.removeEventListener("click", click, { capture: true });
        };
    }
</script>

<svelte:element
    this={as}
    {...rest}
    class={[
        "edge-fade-x flex scrollbar-none gap-2 overflow-x-auto overscroll-x-contain [&::-webkit-scrollbar]:hidden [&>*]:shrink-0",
        dragging && "cursor-grabbing select-none **:cursor-grabbing",
        className,
    ]}
    {@attach drag}
>
    {@render children()}
</svelte:element>
