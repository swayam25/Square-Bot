import { watch, watchStatus } from "#lib/server/live.ts";
import { getRequestEvent, query } from "$app/server";
import { error } from "@sveltejs/kit";
import { z } from "zod";

const guildId = z.string().regex(/^\d{17,20}$/);

function actor() {
    const { session } = getRequestEvent().locals;
    if (!session) error(401, "Log in first");
    return session.user.id;
}

export const livePlayer = query.live(guildId, (guild) => watch(guild, actor(), "player"));

export const liveQueue = query.live(guildId, (guild) => watch(guild, actor(), "queue"));

export const liveStatus = query.live(() => {
    actor();
    return watchStatus();
});
