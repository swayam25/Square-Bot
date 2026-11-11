import { DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET } from "$app/env/private";
import {
    CDNRoutes,
    ImageFormat,
    OAuth2Routes,
    OAuth2Scopes,
    PermissionFlagsBits,
    RouteBases,
    Routes,
    type RESTGetAPICurrentUserGuildsResult,
    type RESTGetAPICurrentUserResult,
} from "discord-api-types/v10";
import * as oauth from "oauth4webapi";

const as: oauth.AuthorizationServer = {
    issuer: "https://discord.com",
    authorization_endpoint: OAuth2Routes.authorizationURL,
    token_endpoint: OAuth2Routes.tokenURL,
    revocation_endpoint: OAuth2Routes.tokenRevocationURL,
    code_challenge_methods_supported: ["S256"],
    authorization_response_iss_parameter_supported: true,
};
const client: oauth.Client = { client_id: DISCORD_CLIENT_ID };
const clientAuth = oauth.ClientSecretBasic(DISCORD_CLIENT_SECRET);

export function authorizationUrl(redirectUri: string, state: string, codeChallenge: string) {
    const url = new URL(OAuth2Routes.authorizationURL);
    url.search = new URLSearchParams({
        client_id: DISCORD_CLIENT_ID,
        response_type: "code",
        redirect_uri: redirectUri,
        scope: [OAuth2Scopes.Identify, OAuth2Scopes.Guilds].join(" "),
        state,
        code_challenge: codeChallenge,
        code_challenge_method: "S256",
        prompt: "none",
    }).toString();
    return url;
}

export async function exchangeCode(callbackUrl: URL, redirectUri: string, state: string, codeVerifier: string) {
    const params = oauth.validateAuthResponse(as, client, callbackUrl, state);
    const response = await oauth.authorizationCodeGrantRequest(as, client, clientAuth, params, redirectUri, codeVerifier);
    return oauth.processAuthorizationCodeResponse(as, client, response);
}

export async function revokeToken(token: string) {
    await oauth.processRevocationResponse(await oauth.revocationRequest(as, client, clientAuth, token));
}

export class DiscordError extends Error {
    constructor(
        route: string,
        readonly status: number,
    ) {
        super(`Discord ${route} returned ${status}`);
    }
}

async function api<T>(route: string, accessToken: string): Promise<T> {
    const response = await fetch(RouteBases.api + route, {
        headers: { Authorization: `Bearer ${accessToken}` },
        signal: AbortSignal.timeout(5_000),
    });
    if (!response.ok) throw new DiscordError(route, response.status);
    return response.json();
}

export const fetchUser = (accessToken: string) => api<RESTGetAPICurrentUserResult>(Routes.user(), accessToken);

export async function fetchManageableGuilds(accessToken: string) {
    const guilds = await api<RESTGetAPICurrentUserGuildsResult>(Routes.userGuilds(), accessToken);
    const manage = PermissionFlagsBits.Administrator | PermissionFlagsBits.ManageGuild;
    return guilds
        .filter((guild) => guild.owner || (BigInt(guild.permissions) & manage) !== 0n)
        .map((guild) => ({
            id: guild.id,
            name: guild.name,
            iconUrl: guild.icon ? RouteBases.cdn + CDNRoutes.guildIcon(guild.id, guild.icon, ImageFormat.WebP) + "?size=128" : null,
        }));
}

export function inviteUrl(guildId?: string) {
    const url = new URL(OAuth2Routes.authorizationURL);
    url.search = new URLSearchParams({
        client_id: DISCORD_CLIENT_ID,
        scope: [OAuth2Scopes.Bot, OAuth2Scopes.ApplicationsCommands].join(" "),
        permissions: PermissionFlagsBits.Administrator.toString(),
        ...(guildId && { guild_id: guildId, disable_guild_select: "true" }),
    }).toString();
    return url;
}

export function avatarUrl(user: { id: string; avatar: string | null }) {
    return user.avatar ? RouteBases.cdn + CDNRoutes.userAvatar(user.id, user.avatar, ImageFormat.WebP) + "?size=128" : null;
}
