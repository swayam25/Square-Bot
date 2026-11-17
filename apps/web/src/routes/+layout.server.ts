import { avatarUrl, inviteUrl } from "#lib/server/discord.ts";
import { squareEmojis } from "#lib/server/emojis.ts";
import type { LayoutServerLoad } from "./$types";

export const load: LayoutServerLoad = async ({ locals }) => {
    const user = locals.session?.user;
    return {
        user: user && {
            id: user.id,
            name: user.globalName ?? user.username,
            username: user.username,
            avatarUrl: avatarUrl(user),
        },
        inviteUrl: inviteUrl().href,
        squareEmojis: await squareEmojis(),
    };
};
