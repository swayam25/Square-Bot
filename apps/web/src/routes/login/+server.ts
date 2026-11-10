import { authorizationUrl } from "#lib/server/discord.ts";
import { setOAuthCookies } from "#lib/server/oauth-cookies.ts";
import { redirect } from "@sveltejs/kit";
import * as oauth from "oauth4webapi";
import type { RequestHandler } from "./$types";

export const GET: RequestHandler = async ({ cookies, url }) => {
    const state = oauth.generateRandomState();
    const codeVerifier = oauth.generateRandomCodeVerifier();
    setOAuthCookies(cookies, state, codeVerifier, url.searchParams.has("popup"));

    const redirectUri = new URL("/auth/callback", url).href;
    redirect(303, authorizationUrl(redirectUri, state, await oauth.calculatePKCECodeChallenge(codeVerifier)), {
        external: ["https://discord.com"],
    });
};
