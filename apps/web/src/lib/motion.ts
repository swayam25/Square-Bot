import type { OnNavigate } from "$app/navigation";
import type { Attachment } from "svelte/attachments";

/**
 * Press feedback for anything clickable: a circle of the element's text color grows from the pointer and fades once
 * it's released. The element needs the `ripple` utility from `layout.css`, which clips the circle to its shape.
 */
export const ripple: Attachment<HTMLElement> = (node) => {
    function press(event: PointerEvent) {
        if (event.button !== 0 || node.matches(":disabled, [aria-disabled='true']")) return;
        if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;

        const box = node.getBoundingClientRect();
        const x = event.clientX - box.left;
        const y = event.clientY - box.top;
        // Far enough to reach the corner furthest from the pointer
        const radius = Math.hypot(Math.max(x, box.width - x), Math.max(y, box.height - y));

        const wave = document.createElement("span");
        wave.setAttribute("aria-hidden", "true");
        wave.className = "ripple-wave";
        Object.assign(wave.style, { left: `${x - radius}px`, top: `${y - radius}px`, width: `${radius * 2}px`, height: `${radius * 2}px` });
        node.append(wave);

        const grow = wave.animate(
            [
                { scale: 0, opacity: 0.2 },
                { scale: 1, opacity: 0.14 },
            ],
            {
                duration: 420,
                easing: "cubic-bezier(0.22, 1, 0.36, 1)",
                fill: "forwards",
            },
        );

        // Fade only after the circle has had time to show, so a quick tap still reads as a press
        function release() {
            removeEventListener("pointerup", release);
            removeEventListener("pointercancel", release);
            grow.finished
                .catch(() => {})
                .then(() => wave.animate([{ opacity: 0.14 }, { opacity: 0 }], { duration: 280, easing: "ease-out", fill: "forwards" }).finished)
                .catch(() => {})
                .finally(() => wave.remove());
        }
        addEventListener("pointerup", release);
        addEventListener("pointercancel", release);
    }

    node.addEventListener("pointerdown", press);
    return () => node.removeEventListener("pointerdown", press);
};

/**
 * `onNavigate` handler for the root layout: swaps pages inside a view transition, so the old page fades out and the
 * new one rises in while the floating header stays put. The animation itself lives in `layout.css`.
 *
 * `onNavigate` runs once the next page's data is loaded, so a slow load shows the loader first and this only
 * animates the swap.
 */
export function pageTransition(navigation: OnNavigate): Promise<void> | void {
    const from = navigation.from?.url.pathname;
    const to = navigation.to?.url.pathname;
    if (!from || !to || from === to || !document.startViewTransition) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    return new Promise((resolve) => {
        const transition = document.startViewTransition(async () => {
            resolve();
            await navigation.complete;
        });
        // A failed navigation rejects these. It reports its own error, so the transition just ends
        transition.ready.catch(() => {});
        transition.finished.catch(() => {});
    });
}
