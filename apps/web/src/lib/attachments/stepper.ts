import type { Attachment } from "svelte/attachments";

const REPEAT_DELAY_MS = 400;
const REPEAT_EVERY_MS = 60;
const WHEEL_NOTCH_PX = 100;
const WHEEL_TRACKPAD_PX = 50;

// Steps on press and keeps stepping while held. Keyboard presses still arrive as a click with `detail` 0
export function holdStep(step: () => void): Attachment<HTMLButtonElement> {
    return (node) => {
        let delay: ReturnType<typeof setTimeout> | undefined;
        let repeat: ReturnType<typeof setInterval> | undefined;

        const stop = () => {
            clearTimeout(delay);
            clearInterval(repeat);
        };
        const tick = () => (node.disabled ? stop() : step());

        function down(event: PointerEvent) {
            if (event.button !== 0 || node.disabled) return;
            node.setPointerCapture(event.pointerId);
            stop();
            step();
            delay = setTimeout(() => (repeat = setInterval(tick, REPEAT_EVERY_MS)), REPEAT_DELAY_MS);
        }

        function click(event: MouseEvent) {
            if (event.detail === 0) step();
        }

        const block = (event: Event) => event.preventDefault();

        node.addEventListener("pointerdown", down);
        node.addEventListener("pointerup", stop);
        node.addEventListener("pointercancel", stop);
        node.addEventListener("lostpointercapture", stop);
        node.addEventListener("click", click);
        node.addEventListener("contextmenu", block);
        return () => {
            stop();
            node.removeEventListener("pointerdown", down);
            node.removeEventListener("pointerup", stop);
            node.removeEventListener("pointercancel", stop);
            node.removeEventListener("lostpointercapture", stop);
            node.removeEventListener("click", click);
            node.removeEventListener("contextmenu", block);
        };
    };
}

// Mouse wheels send whole notches, sometimes several merged into one event; trackpads send small deltas that add up
export function wheelStep(step: (direction: 1 | -1) => void): Attachment<HTMLElement> {
    return (node) => {
        let built = 0;

        function wheel(event: WheelEvent) {
            const delta = event.deltaMode === WheelEvent.DOM_DELTA_LINE ? event.deltaY * 40 : event.deltaY;
            if (!delta) return;
            event.preventDefault();
            const direction = delta < 0 ? 1 : -1;
            if (Math.abs(delta) >= WHEEL_TRACKPAD_PX) {
                built = 0;
                for (let notches = Math.max(1, Math.round(Math.abs(delta) / WHEEL_NOTCH_PX)); notches > 0; notches--) step(direction);
                return;
            }
            if (Math.sign(delta) !== Math.sign(built)) built = 0;
            built += delta;
            if (Math.abs(built) < WHEEL_TRACKPAD_PX) return;
            built = 0;
            step(direction);
        }

        node.addEventListener("wheel", wheel, { passive: false });
        return () => node.removeEventListener("wheel", wheel);
    };
}
