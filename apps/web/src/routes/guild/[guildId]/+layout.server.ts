import { error } from "@sveltejs/kit";
import type { LayoutServerLoad } from "./$types";

export const load: LayoutServerLoad = async ({ params, parent }) => {
    const { guilds } = await parent();
    const guild = guilds.find((guild) => guild.id === params.guildId);
    if (!guild) error(404, "Square isn't in this server, or you aren't a member of it.");
    return { guild };
};
