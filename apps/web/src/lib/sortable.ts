import type { Attachment } from "svelte/attachments";

const SETTLE_MS = 200;
const SETTLE = `transform ${SETTLE_MS}ms cubic-bezier(0.2, 0, 0, 1)`;

interface Options {
    // Must put the list in its new order synchronously (`flushSync`), and without its own move animation:
    // the drop is measured right after it returns
    onmove: (from: number, to: number) => void;
    disabled?: () => boolean;
}

function scrollParent(node: HTMLElement) {
    for (let el = node.parentElement; el; el = el.parentElement) {
        const { overflowY } = getComputedStyle(el);
        if ((overflowY === "auto" || overflowY === "scroll") && el.scrollHeight > el.clientHeight) return el;
    }
    return document.scrollingElement as HTMLElement;
}

export function sortable({ onmove, disabled }: Options): Attachment<HTMLElement> {
    return (list) => {
        let drag: {
            pointer: number;
            item: HTMLElement;
            items: HTMLElement[];
            scroller: HTMLElement;
            mids: number[];
            from: number;
            to: number;
            step: number;
            startY: number;
            clientY: number;
            frame: number;
        } | null = null;

        const contentY = (scroller: HTMLElement, clientY: number) => clientY + scroller.scrollTop;

        function layout() {
            if (!drag) return;
            const dy = contentY(drag.scroller, drag.clientY) - drag.startY;
            drag.item.style.transform = `translateY(${dy}px)`;
            const center = drag.mids[drag.from]! + dy;
            let to = drag.from;
            for (let i = 0; i < drag.items.length; i += 1) {
                if (i > drag.from && center > drag.mids[i]!) to = i;
                if (i < drag.from && center < drag.mids[i]! && to === drag.from) to = i;
            }
            drag.to = to;
            drag.items.forEach((el, i) => {
                if (el === drag!.item) return;
                let shift = 0;
                if (i > drag!.from && i <= to) shift = -drag!.step;
                if (i < drag!.from && i >= to) shift = drag!.step;
                el.style.transform = shift ? `translateY(${shift}px)` : "";
            });
        }

        function autoscroll() {
            if (!drag) return;
            const edge = 72;
            const box = drag.scroller.getBoundingClientRect();
            const top = Math.max(box.top, 0);
            const bottom = Math.min(box.bottom, window.innerHeight);
            const y = drag.clientY;
            const speed = y < top + edge ? -(top + edge - y) / 4 : y > bottom - edge ? (y - (bottom - edge)) / 4 : 0;
            if (speed) {
                drag.scroller.scrollBy(0, speed);
                layout();
            }
            drag.frame = requestAnimationFrame(autoscroll);
        }

        function down(event: PointerEvent) {
            if (drag || event.button !== 0 || disabled?.()) return;
            const handle = (event.target as Element).closest<HTMLElement>("[data-drag-handle]");
            const item = handle?.closest<HTMLElement>("[data-sortable-index]");
            if (!handle || !item || !list.contains(item)) return;
            event.preventDefault();
            const items = [...list.children].filter((el): el is HTMLElement => el instanceof HTMLElement && el.hasAttribute("data-sortable-index"));
            const rects = items.map((el) => el.getBoundingClientRect());
            const from = items.indexOf(item);
            const next = rects[from + 1] ?? rects[from - 1];
            const gap = next ? Math.abs(rects[from + 1] ? next.top - rects[from]!.bottom : rects[from]!.top - next.bottom) : 0;
            const scroller = scrollParent(list);
            handle.setPointerCapture(event.pointerId);
            drag = {
                pointer: event.pointerId,
                item,
                items,
                scroller,
                mids: rects.map((r) => contentY(scroller, r.top) + r.height / 2),
                from,
                to: from,
                step: rects[from]!.height + gap,
                startY: contentY(scroller, event.clientY),
                clientY: event.clientY,
                frame: 0,
            };
            item.dataset.dragging = "";
            for (const el of items) el.style.transition = el === item ? "none" : SETTLE;
            drag.frame = requestAnimationFrame(autoscroll);
        }

        function move(event: PointerEvent) {
            if (!drag || event.pointerId !== drag.pointer) return;
            drag.clientY = event.clientY;
            layout();
        }

        function up(event: PointerEvent) {
            if (!drag || event.pointerId !== drag.pointer) return;
            const { from, to, items, item, frame } = drag;
            cancelAnimationFrame(frame);
            drag = null;
            delete item.dataset.dragging;
            const settle = () => {
                if (!drag) for (const el of items) el.style.transition = "";
            };

            if (event.type !== "pointerup" || to === from) {
                for (const el of items) {
                    el.style.transition = SETTLE;
                    el.style.transform = "";
                }
                setTimeout(settle, SETTLE_MS);
                return;
            }

            const before = items.map((el) => el.getBoundingClientRect().top);
            for (const el of items) {
                el.style.transition = "none";
                el.style.transform = "";
            }
            onmove(from, to);
            const offsets = items.map((el, i) => before[i]! - el.getBoundingClientRect().top);
            items.forEach((el, i) => {
                if (Math.abs(offsets[i]!) > 0.5) el.style.transform = `translateY(${offsets[i]}px)`;
            });
            void list.offsetHeight;
            for (const el of items) {
                el.style.transition = SETTLE;
                el.style.transform = "";
            }
            setTimeout(settle, SETTLE_MS);
        }

        function key(event: KeyboardEvent) {
            const item = (event.target as Element).closest<HTMLElement>("[data-drag-handle]")?.closest<HTMLElement>("[data-sortable-index]");
            if (!item || disabled?.()) return;
            const from = Number(item.dataset.sortableIndex);
            const count = list.querySelectorAll("[data-sortable-index]").length;
            const to = event.key === "ArrowUp" ? from - 1 : event.key === "ArrowDown" ? from + 1 : -1;
            if (to < 0 || to >= count) return;
            event.preventDefault();
            onmove(from, to);
        }

        list.addEventListener("pointerdown", down);
        list.addEventListener("pointermove", move);
        list.addEventListener("pointerup", up);
        list.addEventListener("pointercancel", up);
        list.addEventListener("keydown", key);
        return () => {
            if (drag) cancelAnimationFrame(drag.frame);
            list.removeEventListener("pointerdown", down);
            list.removeEventListener("pointermove", move);
            list.removeEventListener("pointerup", up);
            list.removeEventListener("pointercancel", up);
            list.removeEventListener("keydown", key);
        };
    };
}
