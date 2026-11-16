import { untrack } from "svelte";

class Overlays {
    open = $state(0);

    /** Counts a drawer or dialog while it is open. Call inside an effect and return the result as its cleanup. */
    hold() {
        untrack(() => this.open++);
        return () => untrack(() => this.open--);
    }
}

export const overlays = new Overlays();
