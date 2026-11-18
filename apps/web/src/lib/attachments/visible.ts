import type { Attachment } from "svelte/attachments";

// Fires again only on a fresh observe, so key the node on what it loads to re-check while it stays in view
export function visible(callback: () => void, margin = "200px"): Attachment<HTMLElement> {
    return (node) => {
        const observer = new IntersectionObserver((entries) => entries.some((entry) => entry.isIntersecting) && callback(), {
            rootMargin: margin,
        });
        observer.observe(node);
        return () => observer.disconnect();
    };
}
