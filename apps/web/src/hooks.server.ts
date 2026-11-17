import { getSession, SESSION_COOKIE } from "#lib/server/session.ts";
import { error } from "@sveltejs/kit";
import type { Handle } from "@sveltejs/kit/hooks";

const PRELOADED_FONTS = /\/(saira|noto-sans|jetbrains-mono)-latin-wght-normal\.[\w-]+\.woff2$/;

export const handle: Handle = async ({ event, resolve }) => {
    const token = event.cookies.get(SESSION_COOKIE);
    event.locals.session = token
        ? await getSession(token).catch(() => error(503, "The dashboard can't reach its session store right now. Try again in a moment."))
        : null;
    if (token && !event.locals.session) event.cookies.delete(SESSION_COOKIE, { path: "/" });
    return resolve(event, {
        preload: ({ type, path }) => type === "js" || type === "css" || (type === "font" && PRELOADED_FONTS.test(path)),
    });
};
