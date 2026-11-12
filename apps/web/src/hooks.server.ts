import { getSession, SESSION_COOKIE } from "#lib/server/session.ts";
import type { Handle } from "@sveltejs/kit/hooks";

export const handle: Handle = async ({ event, resolve }) => {
    const token = event.cookies.get(SESSION_COOKIE);
    event.locals.session = token ? await getSession(token) : null;
    if (token && !event.locals.session) event.cookies.delete(SESSION_COOKIE, { path: "/" });
    const response = await resolve(event);
    response.headers.set("x-frame-options", "DENY");
    response.headers.set("x-content-type-options", "nosniff");
    response.headers.set("referrer-policy", "strict-origin-when-cross-origin");
    return response;
};
