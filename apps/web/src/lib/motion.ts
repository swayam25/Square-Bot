import type { Attachment } from "svelte/attachments";

// Needs the `ripple` utility from `layout.css`, which clips the wave to the element
export const ripple: Attachment<HTMLElement> = (node) => {
    function press(event: PointerEvent) {
        if (event.button !== 0 || node.matches(":disabled, [aria-disabled='true']")) return;
        if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;

        const box = node.getBoundingClientRect();
        const x = event.clientX - box.left;
        const y = event.clientY - box.top;
        const radius = Math.hypot(Math.max(x, box.width - x), Math.max(y, box.height - y)) * 1.1;
        const pressed = performance.now();

        const wave = document.createElement("span");
        wave.setAttribute("aria-hidden", "true");
        wave.className = "ripple-wave";
        Object.assign(wave.style, { left: `${x - radius}px`, top: `${y - radius}px`, width: `${radius * 2}px`, height: `${radius * 2}px` });
        node.append(wave);

        const grow = wave.animate(
            [
                { scale: 0.15, opacity: 0.16 },
                { scale: 1, opacity: 0.12 },
            ],
            {
                duration: 450,
                easing: "cubic-bezier(0.22, 1, 0.36, 1)",
                fill: "forwards",
            },
        );

        function release() {
            removeEventListener("pointerup", release);
            removeEventListener("pointercancel", release);
            const fade = () =>
                wave
                    .animate([{ opacity: getComputedStyle(wave).opacity }, { opacity: 0 }], { duration: 240, easing: "ease-out", fill: "forwards" })
                    .finished.catch(() => {})
                    .finally(() => {
                        grow.cancel();
                        wave.remove();
                    });
            setTimeout(fade, Math.max(0, 120 - (performance.now() - pressed)));
        }
        addEventListener("pointerup", release);
        addEventListener("pointercancel", release);
    }

    node.addEventListener("pointerdown", press);
    return () => node.removeEventListener("pointerdown", press);
};
