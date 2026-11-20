import { avatarUrl, installUrl, inviteUrl } from "#lib/server/discord.ts";
import { squareEmojis } from "#lib/server/emojis.ts";
import type { LayoutServerLoad } from "./$types";

export const load: LayoutServerLoad = async ({ locals, url }) => {
    const user = locals.session?.user;
    return {
        user: user && {
            id: user.id,
            name: user.globalName ?? user.username,
            username: user.username,
            avatarUrl: avatarUrl(user),
        },
        inviteUrl: inviteUrl(url.origin).href,
        installUrl: installUrl(url.origin).href,
        squareEmojis: await squareEmojis(),
    };
};
