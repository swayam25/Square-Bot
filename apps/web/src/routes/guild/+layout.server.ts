import { bot } from "#lib/server/bot.ts";
import { myGuilds } from "@square/api-client";
import { error, redirect } from "@sveltejs/kit";
import type { LayoutServerLoad } from "./$types";

export const load: LayoutServerLoad = async ({ locals }) => {
    if (!locals.session) redirect(303, "/login");

    const { data } = await myGuilds({ client: bot, headers: { "x-actor-id": locals.session.user.id } }).catch(() => ({ data: undefined }));
    if (!data) error(503, "Square is offline right now. Try again in a minute.");

    return { guilds: data.toSorted((a, b) => a.name.localeCompare(b.name)) };
};
