ARG NODE_IMAGE=node:24-slim@sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54
ARG CADDY_IMAGE=caddy:2.11-alpine@sha256:003a97808e781aa9f7e75cc2f43d34d461099031faf5e20faefb9f61126836f0

FROM ${NODE_IMAGE} AS base
ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH \
    COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    CI=true
WORKDIR /app
COPY package.json ./
# Pins pnpm to the root `packageManager` in this layer, so later stages never download it again
RUN corepack enable && corepack install

FROM base AS manifests
COPY pnpm-lock.yaml pnpm-workspace.yaml ./
# The lockfile lists every workspace package, so a frozen install needs all their manifests
COPY apps/bot/package.json ./apps/bot/
COPY apps/web/package.json ./apps/web/
COPY packages/api-client/package.json ./packages/api-client/

FROM manifests AS deps
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile --prod --filter "web..."

FROM manifests AS build
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile --filter "web..."
COPY packages ./packages
COPY apps/web ./apps/web
RUN pnpm --filter web run build

FROM ${NODE_IMAGE} AS web
ENV NODE_ENV=production \
    PORT=3000
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages/api-client/node_modules ./packages/api-client/node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules
COPY --from=build /app/apps/web/build ./apps/web/build
COPY apps/web/package.json ./apps/web/
WORKDIR /app/apps/web
USER node
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000/robots.txt').then((r) => process.exit(r.ok ? 0 : 1), () => process.exit(1))"]
CMD ["node", "build"]

FROM ${CADDY_IMAGE} AS proxy
COPY apps/web/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/apps/web/build/client /srv
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD ["wget", "-q", "--spider", "http://127.0.0.1/healthz"]
