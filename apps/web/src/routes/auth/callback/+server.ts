import { exchangeCode, fetchUser, INSTALL_STATE, INVITE_STATE, redeemInstall } from "#lib/server/discord.ts";
import { takeOAuthCookies } from "#lib/server/oauth-cookies.ts";
import { createSession, deleteSession } from "#lib/server/session.ts";
import { error, redirect } from "@sveltejs/kit";
import * as oauth from "oauth4webapi";
import type { RequestHandler } from "./$types";

async function finishInstall(url: URL) {
    // No code means the user cancelled on Discord's page
    const code = url.searchParams.get("code");
    if (!code) return false;
    const added = await redeemInstall(code, new URL("/auth/callback", url).href).catch(() => false);
    if (!added) console.warn("Discord install rejected");
    return added;
}

export const GET: RequestHandler = async ({ cookies, url }) => {
    // A finished or cancelled bot invite, not a login. Its code is never exchanged, the bot needs no user token
    if (url.searchParams.get("state") === INVITE_STATE) {
        const guild = url.searchParams.get("guild_id");
        redirect(303, guild && /^\d{17,20}$/.test(guild) ? `/auth/done?guild=${guild}` : "/auth/done?invite");
    }

    if (url.searchParams.get("state") === INSTALL_STATE) {
        redirect(303, `/auth/done?install=${(await finishInstall(url)) ? "added" : "cancelled"}`);
    }

    const login = takeOAuthCookies(cookies);
    if (!login) error(400, "This login link expired. Try logging in again.");

    const done = login.popup ? "/auth/done" : "/guild";
    const redirectUri = new URL("/auth/callback", url).href;
    let tokens: oauth.TokenEndpointResponse;
    try {
        tokens = await exchangeCode(url, redirectUri, login.state, login.codeVerifier);
    } catch (err) {
        if (err instanceof oauth.AuthorizationResponseError && err.error === "access_denied") redirect(303, login.popup ? done : "/");
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
