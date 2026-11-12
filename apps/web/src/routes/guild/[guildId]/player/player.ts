import { errorMessage } from "#lib/errors.ts";
import { toast } from "#lib/toast.svelte.ts";
import type { PlayerState } from "@square/api-client";

export type Tab = "search" | "queue" | "history" | "lyrics";

export type Access = { dj: boolean; inChannel: boolean; me: string | null };

export function locked(access: Access, { own = false } = {}): string | null {
    if (!access.inChannel) return "Join the bot's voice channel first";
    if (!access.dj && !own) return "Only a DJ can do that";
    return null;
}

export function skipping(player: PlayerState, access: Access) {
    const now = access.dj || (!!access.me && player.track?.requester?.id === access.me);
    const voted = !!access.me && !!player.vote?.voterIds.includes(access.me);
    const deafened = player.viewer.deafened ? "Undeafen to vote on a skip" : null;
    const lock = locked(access, { own: true }) ?? (now ? null : voted ? "You already voted" : deafened);
    return { now, voted, lock };
}

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
