import { avatarUrl } from "#lib/server/discord.ts";
import type { LayoutServerLoad } from "./$types";

export const load: LayoutServerLoad = ({ locals }) => {
    const user = locals.session?.user;
    return {
        user: user && {
            id: user.id,
            name: user.globalName ?? user.username,
            username: user.username,
            avatarUrl: avatarUrl(user),
        },
    };
};
