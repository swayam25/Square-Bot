import { errorMessage } from "#lib/errors.ts";
import { toast } from "#lib/toast.svelte.ts";
import type { PlayerState } from "@square/api-client";

export type Tab = "search" | "queue" | "history" | "lyrics";

export type Access = { dj: boolean; inChannel: boolean; me: string | null };

// Why a control is locked for this viewer, or null when they may use it. `own` marks an action on their own track
export function locked(access: Access, { own = false } = {}): string | null {
    if (!access.inChannel) return "Join the bot's voice channel first";
    if (!access.dj && !own) return "Only a DJ can do that";
    return null;
}

// DJs and whoever queued the song skip it outright. Everyone else starts or joins a vote
export function skipping(player: PlayerState, access: Access) {
    const now = access.dj || (!!access.me && player.track?.requester?.id === access.me);
    const voted = !!access.me && !!player.vote?.voterIds.includes(access.me);
    const deafened = player.viewer.deafened ? "Undeafen to vote on a skip" : null;
    const lock = locked(access, { own: true }) ?? (now ? null : voted ? "You already voted" : deafened);
    return { now, voted, lock };
}

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
