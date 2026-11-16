import type { Attachment } from "svelte/attachments";

// Chrome keeps a scroll-driven animation's last value once nothing overflows, which leaves a stale fade behind
export function edgeFade(axis: "x" | "y"): Attachment<HTMLElement> {
    return (node) => {
        const sync = () => {
            const overflow = axis === "x" ? node.scrollWidth - node.clientWidth : node.scrollHeight - node.clientHeight;
            node.toggleAttribute("data-fade-off", overflow <= 1);
        };
        const resize = new ResizeObserver(sync);
        const watch = () => {
            resize.disconnect();
            resize.observe(node);
            for (const child of node.children) resize.observe(child);
        };
        const children = new MutationObserver(() => {
            watch();
            sync();
        });
        watch();
        sync();
        children.observe(node, { childList: true });
        return () => {
            resize.disconnect();
            children.disconnect();
        };
    };
}
