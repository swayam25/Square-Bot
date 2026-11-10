import { REDIS_URL } from "$app/env/private";
import { createClient } from "@redis/client";

let connected = false;

export const redis = createClient({
    url: REDIS_URL,
    socket: { reconnectStrategy: (retries, cause) => (connected ? Math.min(retries * 100, 3_000) : cause) },
}).on("error", (err) => console.error("Redis error:", err));

await redis.connect();
connected = true;

// An open socket keeps Node alive, so a SIGTERM would otherwise wait for the shutdown timeout
process.once("sveltekit:shutdown", () => redis.close());
