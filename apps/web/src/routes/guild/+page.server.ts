import { DiscordError, fetchManageableGuilds, inviteUrl } from "#lib/server/discord.ts";
import { redis } from "#lib/server/redis.ts";
import { deleteSession, type Session } from "#lib/server/session.ts";
import { redirect } from "@sveltejs/kit";
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

export const load: PageServerLoad = async ({ locals, cookies, parent }) => {
    const session = locals.session;
    if (!session) redirect(303, "/login");

    const [[discord], { guilds }] = await Promise.all([Promise.allSettled([manageableGuilds(session)]), parent()]);

    if (discord.status === "rejected") {
        // The user removed Square from their Discord authorized apps
        if (discord.reason instanceof DiscordError && discord.reason.status === 401) {
            await deleteSession(cookies);
            redirect(303, "/login");
        }
        throw discord.reason;
    }

    const added = new Set(guilds.map((guild) => guild.id));
    return {
        inviteUrl: inviteUrl().href,
        invitable: discord.value
            .filter((guild) => !added.has(guild.id))
            .map((guild) => ({ ...guild, inviteUrl: inviteUrl(guild.id).href }))
            .toSorted((a, b) => a.name.localeCompare(b.name)),
    };
};
