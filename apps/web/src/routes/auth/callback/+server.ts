import { exchangeCode, fetchUser } from "#lib/server/discord.ts";
import { takeOAuthCookies } from "#lib/server/oauth-cookies.ts";
import { createSession, deleteSession } from "#lib/server/session.ts";
import { error, redirect } from "@sveltejs/kit";
import * as oauth from "oauth4webapi";
import type { RequestHandler } from "./$types";

export const GET: RequestHandler = async ({ cookies, url }) => {
    const login = takeOAuthCookies(cookies);
    if (!login) error(400, "This login link expired. Try logging in again.");

    // A popup login ends on a page that tells the opener and closes itself
    const done = login.popup ? "/auth/done" : "/servers";
    const redirectUri = new URL("/auth/callback", url).href;
    let tokens: oauth.TokenEndpointResponse;
    try {
        tokens = await exchangeCode(url, redirectUri, login.state, login.codeVerifier);
    } catch (err) {
        // The user pressed Cancel on Discord's screen
        if (err instanceof oauth.AuthorizationResponseError && err.error === "access_denied") redirect(303, login.popup ? done : "/");
        // Wrong `state` or `iss`, a reused code, and the like
        if (
            err instanceof oauth.AuthorizationResponseError ||
            err instanceof oauth.OperationProcessingError ||
            err instanceof oauth.ResponseBodyError
        ) {
            console.warn("Discord login rejected:", err.message);
            error(400, "Login failed. Try logging in again.");
        }
        throw err;
    }

    const user = await fetchUser(tokens.access_token);
    // A fresh token on every login, so a session ID planted before login is useless
    await deleteSession(cookies);
    await createSession(
        cookies,
        {
            user: { id: user.id, username: user.username, globalName: user.global_name, avatar: user.avatar },
            accessToken: tokens.access_token,
        },
        tokens.expires_in,
    );
    redirect(303, done);
};
