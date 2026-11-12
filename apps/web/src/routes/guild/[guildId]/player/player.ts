import { errorMessage } from "#lib/errors.ts";
import { toast } from "#lib/toast.svelte.ts";

export type Tab = "search" | "queue" | "lyrics";

export const time = (ms: number) => {
    const seconds = Math.max(0, Math.floor(ms / 1000));
    const hours = Math.floor(seconds / 3600);
    const rest = `${Math.floor((seconds % 3600) / 60)}:${String(seconds % 60).padStart(2, "0")}`;
    return hours ? `${hours}:${rest.padStart(5, "0")}` : rest;
};

// Refusals always show, with the bot's reason. Confirmations only show when asked for: the player itself already
// shows a pause or a skip, so announcing those too would be noise.
export async function control(action: Promise<{ message: string; note: string | null } | undefined>, { announce = false } = {}) {
    try {
        const done = await action;
        if (announce && done) toast.success(done.message, { description: done.note ?? undefined });
        return true;
    } catch (err) {
        toast.error(errorMessage(err, "Square couldn't do that. Try again."));
        return false;
    }
}
