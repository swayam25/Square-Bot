import { REDIS_URL } from "$app/env/private";
import { createClient } from "@redis/client";

let connected = false;

export const redis = createClient({
    url: REDIS_URL,
    // While Redis is away commands are refused at once instead of piling up until it returns
    disableOfflineQueue: true,
    // A Redis that is up but silent never answers a sent command, so the socket is dropped after 5s of nothing.
    // The ping keeps a healthy idle connection from tripping that
    pingInterval: 2_000,
    socket: {
        socketTimeout: 5_000,
        reconnectStrategy: (retries, cause) => (connected ? Math.min(retries * 100, 3_000) : cause),
    },
}).on("error", (err) => console.error("Redis error:", err));

await redis.connect();
connected = true;

// An open socket keeps Node alive, so a SIGTERM would otherwise wait for the shutdown timeout
process.once("sveltekit:shutdown", () => redis.close());
