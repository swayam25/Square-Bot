import type { ServerInit } from "@sveltejs/kit/hooks";

export const init: ServerInit = async () => {
    await import("#lib/server/redis.ts");
};
