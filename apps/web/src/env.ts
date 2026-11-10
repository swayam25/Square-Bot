import { building } from "$app/env";
import { defineEnvVars } from "@sveltejs/kit/env";

// Builds (CI, Docker) don't have runtime secrets, so values are only checked when the app starts
function runtime<T>(parse: (value: string | undefined) => T) {
    return (value: string | undefined) => (building ? (value as T) : parse(value));
}

export const variables = defineEnvVars({
    BOT_API_URL: {
        description: "Base URL of the bot's API",
        schema: runtime((value) => new URL(value ?? "").origin),
    },
    BOT_API_SECRET: {
        description: "Same value as `[api] secret` in the bot's config.toml",
        schema: runtime((value) => {
            if (!value || value.length < 32) throw new Error("must be at least 32 characters");
            return value;
        }),
    },
    REDIS_URL: {
        description: "Redis connection URL, e.g. redis://localhost:6379",
        schema: runtime((value) => {
            if (!value || !/^rediss?:\/\//.test(value)) throw new Error("must start with redis:// or rediss://");
            return value;
        }),
    },
    DISCORD_CLIENT_ID: {
        description: "Application ID from the Discord Developer Portal (the bot's user ID)",
        schema: runtime((value) => {
            if (!value || !/^\d{17,20}$/.test(value)) throw new Error("must be a Discord application ID");
            return value;
        }),
    },
    DISCORD_CLIENT_SECRET: {
        description: "OAuth2 client secret from the Discord Developer Portal",
        schema: runtime((value) => {
            if (!value) throw new Error("is required");
            return value;
        }),
    },
});
