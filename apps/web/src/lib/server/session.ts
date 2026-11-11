import { createHash, randomBytes } from "node:crypto";
import { redis } from "#lib/server/redis.ts";
import type { Cookies } from "@sveltejs/kit";

export const SESSION_COOKIE = "session";
const MAX_AGE = 7 * 24 * 60 * 60;

export interface Session {
    user: {
        id: string;
        username: string;
        globalName: string | null;
        avatar: string | null;
    };
    accessToken: string;
}

// Redis only ever sees the hash, so a leaked dump holds no usable cookies
const key = (token: string) => `session:${createHash("sha256").update(token).digest("hex")}`;

export async function createSession(cookies: Cookies, session: Session, expiresIn = MAX_AGE) {
    const token = randomBytes(32).toString("base64url");
    const maxAge = Math.min(expiresIn, MAX_AGE);
    await redis.set(key(token), JSON.stringify(session), { expiration: { type: "EX", value: maxAge } });
    cookies.set(SESSION_COOKIE, token, { path: "/", httpOnly: true, sameSite: "lax", maxAge });
}

export async function getSession(token: string): Promise<Session | null> {
    const value = await redis.get(key(token));
    return value ? JSON.parse(value) : null;
}

export async function deleteSession(cookies: Cookies) {
    const token = cookies.get(SESSION_COOKIE);
    cookies.delete(SESSION_COOKIE, { path: "/" });
    if (!token) return null;
    const session = await getSession(token);
    await redis.del(key(token));
    return session;
}
