import { prefersReducedMotion } from "svelte/motion";

const TAKEOVER = ["wheel", "touchstart", "keydown", "pointerdown"] as const;

let ease: ((t: number) => number) | undefined;
let cancel: (() => void) | undefined;

// Reads the evenly spaced points of the `--ease-smooth` token so page scrolls move like the rest of the site
function curve() {
    if (ease) return ease;
    const points = (
        getComputedStyle(document.documentElement)
            .getPropertyValue("--ease-smooth")
            .match(/-?\d*\.?\d+/g) ?? []
    ).map(Number);
    if (points.length < 2) return (ease = (t) => 1 - (1 - t) ** 3);
    return (ease = (t) => {
        const x = t * (points.length - 1);
        const index = Math.min(Math.floor(x), points.length - 2);
        return points[index] + (points[index + 1] - points[index]) * (x - index);
    });
}

function destination(element: Element) {
    const margin = parseFloat(getComputedStyle(element).scrollMarginTop) || 0;
    const max = document.documentElement.scrollHeight - innerHeight;
    return Math.max(0, Math.min(max, scrollY + element.getBoundingClientRect().top - margin));
}

/** Scrolls the window to `element` (honoring its scroll margin). Resolves false when the user scrolls, taps or types mid-way */
export function scrollToElement(element: Element): Promise<boolean> {
    cancel?.();
    const from = scrollY;
    const distance = Math.abs(destination(element) - from);
    if (prefersReducedMotion.current || distance < 1) {
        scrollTo({ top: destination(element), behavior: "instant" });
        return Promise.resolve(true);
    }
    const duration = Math.min(900, 500 + distance / 10);
    const progress = curve();

    return new Promise((resolve) => {
        let frame = 0;
        let start: number | undefined;
        const stop = (done: boolean) => {
            cancelAnimationFrame(frame);
            for (const type of TAKEOVER) removeEventListener(type, interrupt);
            cancel = undefined;
            resolve(done);
        };
        const interrupt = () => stop(false);
        // The target is measured every frame so late layout shifts (fonts, rows opening) still land on it
        const step = (now: number) => {
            start ??= now;
            const t = Math.min(1, (now - start) / duration);
            scrollTo({ top: from + (destination(element) - from) * progress(t), behavior: "instant" });
            if (t < 1) frame = requestAnimationFrame(step);
            else stop(true);
        };
        for (const type of TAKEOVER) addEventListener(type, interrupt, { passive: true });
        cancel = interrupt;
        frame = requestAnimationFrame(step);
    });
}
