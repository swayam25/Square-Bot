import type { Attachment } from "svelte/attachments";

const DISTANCE = 40;

// Pair with `touch-pan-y`, or the browser takes sideways moves for itself and the swipe never ends
export function swipe(turn: (step: 1 | -1) => boolean): Attachment<HTMLElement> {
    return (node) => {
        let start: { id: number; x: number; y: number } | null = null;

        function down(event: PointerEvent) {
            if (event.pointerType !== "touch" || !event.isPrimary) return;
            start = { id: event.pointerId, x: event.clientX, y: event.clientY };
        }

        function up(event: PointerEvent) {
            if (!start || event.pointerId !== start.id) return;
            const dx = event.clientX - start.x;
            const dy = event.clientY - start.y;
            start = null;
            if (Math.abs(dx) < DISTANCE || Math.abs(dx) < Math.abs(dy) * 1.5) return;

            // A swipe that ends on a button would also press it
            const swallow = (click: Event) => {
                click.stopPropagation();
                click.preventDefault();
            };
            node.addEventListener("click", swallow, { capture: true, once: true });
            setTimeout(() => node.removeEventListener("click", swallow, { capture: true }));

            const step = dx < 0 ? 1 : -1;
            if (!turn(step) || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
            node.animate(
                [
                    { translate: `${step * 32}px 0`, opacity: 0 },
                    { translate: "0 0", opacity: 1 },
                ],
                { duration: 300, easing: "cubic-bezier(0.22, 1, 0.36, 1)" },
            );
        }

        function cancel() {
            start = null;
        }

        node.addEventListener("pointerdown", down);
        node.addEventListener("pointerup", up);
        node.addEventListener("pointercancel", cancel);
        return () => {
            node.removeEventListener("pointerdown", down);
            node.removeEventListener("pointerup", up);
            node.removeEventListener("pointercancel", cancel);
        };
    };
}
