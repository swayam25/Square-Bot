import { bot } from "#lib/server/bot.ts";
import { DiscordError, fetchManageableGuilds, inviteUrl } from "#lib/server/discord.ts";
import { redis } from "#lib/server/redis.ts";
import { deleteSession, type Session } from "#lib/server/session.ts";
import { myGuilds } from "@square/api-client";
import { error, redirect } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";

// Discord rate limits this per user, so a reload shouldn't refetch it
async function manageableGuilds(session: Session) {
    const key = `guilds:${session.user.id}`;
    const cached = await redis.get(key);
    if (cached) return JSON.parse(cached) as Awaited<ReturnType<typeof fetchManageableGuilds>>;

    const guilds = await fetchManageableGuilds(session.accessToken);
    await redis.set(key, JSON.stringify(guilds), { expiration: { type: "EX", value: 5 * 60 } });
    return guilds;
}

export const load: PageServerLoad = async ({ locals, cookies }) => {
    const session = locals.session;
    if (!session) return { user: null };

    const [square, discord] = await Promise.allSettled([
        myGuilds({ client: bot, headers: { "x-actor-id": session.user.id } }),
        manageableGuilds(session),
    ]);

    if (discord.status === "rejected") {
        // The user removed Square from their Discord authorized apps
        if (discord.reason instanceof DiscordError && discord.reason.status === 401) {
            await deleteSession(cookies);
            redirect(303, "/login");
        }
        throw discord.reason;
    }
    if (square.status === "rejected" || !square.value.data) error(503, "Square is offline right now. Try again in a minute.");

    const added = new Set(square.value.data.map((guild) => guild.id));
    return {
        user: session.user,
        guilds: square.value.data,
        invitable: discord.value.filter((guild) => !added.has(guild.id)).map((guild) => ({ ...guild, inviteUrl: inviteUrl(guild.id).href })),
    };
};
