import { getSession, SESSION_COOKIE } from "#lib/server/session.ts";
import { error } from "@sveltejs/kit";
import type { Handle } from "@sveltejs/kit/hooks";

export const handle: Handle = async ({ event, resolve }) => {
    const token = event.cookies.get(SESSION_COOKIE);
    event.locals.session = token
        ? await getSession(token).catch(() => error(503, "The dashboard can't reach its session store right now. Try again in a moment."))
        : null;
    if (token && !event.locals.session) event.cookies.delete(SESSION_COOKIE, { path: "/" });
    return resolve(event);
};
