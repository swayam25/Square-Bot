import { revokeToken } from "#lib/server/discord.ts";
import { deleteSession } from "#lib/server/session.ts";
import { redirect } from "@sveltejs/kit";
import type { RequestHandler } from "./$types";

// POST only: SvelteKit's origin check blocks cross-site form posts, so other sites can't log users out
export const POST: RequestHandler = async ({ cookies }) => {
    const session = await deleteSession(cookies);
    if (session) await revokeToken(session.accessToken).catch((err) => console.error("Discord token revoke failed:", err));
    redirect(303, "/");
};
