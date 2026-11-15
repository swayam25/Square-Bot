import type { Attachment } from "svelte/attachments";

// Instead of `onload`/`onerror` on <img>: those make server-rendered HTML carry inline handlers the CSP blocks
export const imageLoad =
    (onload?: () => void, onerror?: () => void): Attachment<HTMLImageElement> =>
    (img) => {
        if (img.complete && img.getAttribute("src")) (img.naturalWidth ? onload : onerror)?.();
        const load = () => onload?.();
        const error = () => onerror?.();
        img.addEventListener("load", load);
        img.addEventListener("error", error);
        return () => {
            img.removeEventListener("load", load);
            img.removeEventListener("error", error);
        };
    };
