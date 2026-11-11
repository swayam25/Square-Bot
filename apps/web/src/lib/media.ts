import { MediaQuery } from "svelte/reactivity";

/**
 * Below Tailwind's `md`. Popups and dialogs become drawers there. The server renders the desktop variant, which is
 * fine: everything that switches starts closed.
 */
export const mobile = new MediaQuery("max-width: 767.98px", false);
