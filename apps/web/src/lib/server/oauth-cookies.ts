import type { Cookies } from "@sveltejs/kit";

const STATE = "oauth_state";
const VERIFIER = "oauth_verifier";
const POPUP = "oauth_popup";
const options = { path: "/auth/callback", httpOnly: true, sameSite: "lax", maxAge: 10 * 60 } as const;

export function setOAuthCookies(cookies: Cookies, state: string, codeVerifier: string, popup: boolean) {
    cookies.set(STATE, state, options);
    cookies.set(VERIFIER, codeVerifier, options);
    if (popup) cookies.set(POPUP, "1", options);
    else cookies.delete(POPUP, { path: options.path });
}

export function takeOAuthCookies(cookies: Cookies) {
    const state = cookies.get(STATE);
    const codeVerifier = cookies.get(VERIFIER);
    const popup = cookies.get(POPUP) === "1";
    for (const name of [STATE, VERIFIER, POPUP]) cookies.delete(name, { path: options.path });
    return state && codeVerifier ? { state, codeVerifier, popup } : null;
}
