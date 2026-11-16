import type { Attachment } from "svelte/attachments";

const CONTROL = "input, textarea, select, button, a[href], [contenteditable='true'], [role='spinbutton'], [tabindex]:not([tabindex='-1'])";

// Presses on a field box's padding, counters or icons focus its control instead of doing nothing
export const passPress =
    (target: () => HTMLElement | null | undefined, onpress?: () => void): Attachment<HTMLElement> =>
    (node) => {
        const down = (event: PointerEvent) => {
            const hit = (event.target as Element).closest(CONTROL);
            if (event.button !== 0 || (hit && node.contains(hit))) return;
            event.preventDefault();
            target()?.focus();
            onpress?.();
        };
        node.addEventListener("pointerdown", down);
        return () => node.removeEventListener("pointerdown", down);
    };
