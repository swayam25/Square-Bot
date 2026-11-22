set shell := ["bash", "-euo", "pipefail", "-c"]

[private]
default:
    @just --list --list-heading $'\n\033[1;96mSquare\033[0m \033[2m/ Available Commands\033[0m\n' --list-prefix $'  \033[36m›\033[0m '

[private]
_cache:
    @mkdir -p apps/bot/.cache

[private]
_prep: _cache
    @printf '\033[43m\033[30m SYNC \033[0m \033[33mInstalling dependencies and git hooks\033[0m\n'
    @uv --directory apps/bot sync
    @pnpm install
    @printf '\033[42m\033[30m  OK  \033[0m \033[32mDone\033[0m\n'

# Create the bot and dashboard config from the examples (--dev for local development)
init *args: _cache
    #!/usr/bin/env bash
    set -euo pipefail
    bot=apps/bot/config.toml
    env=apps/web/.env.production
    if [[ "{{ args }}" == *--dev* ]]; then
        env=apps/web/.env
        just _prep
    fi
    if [[ -e $bot || -e $env ]]; then
        read -rp "$bot or $env already exists. Overwrite? [y/N] " reply || true
        [[ ${reply:-} == [yY]* ]] || { printf '\033[42m\033[30m  OK  \033[0m \033[32mKept the existing config\033[0m\n'; exit 0; }
    fi
    secret=$(od -An -tx1 -N32 /dev/urandom | tr -d ' \n')
    umask 077
    sed -e '/^# Uncomment to serve the API/d' -e '/^# \[api\]/,/^# docs/s/^# //' -e "s/^secret = \"\"/secret = \"$secret\"/" apps/bot/config.example.toml > "$bot"
    sed -e "s/^BOT_API_SECRET=$/BOT_API_SECRET=$secret/" apps/web/.env.example > "$env"
    printf '\033[42m\033[30m  OK  \033[0m \033[32mWrote %s and %s, fill in the empty keys\033[0m\n' "$bot" "$env"

# Rebuild and deploy the production stack (--dev for local services)
up *args: _cache
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ "{{ args }}" == *--dev* ]]; then
        printf '\033[43m\033[30m INFO \033[0m \033[33mStarting services\033[0m\n'
        docker compose up -d --build
        printf '\033[42m\033[30m  OK  \033[0m \033[32mServices ready\033[0m\n'
    else
        docker network inspect edge > /dev/null 2>&1 || docker network create edge > /dev/null
        printf '\033[43m\033[30m BLD  \033[0m \033[33mRebuilding images\033[0m\n'
        docker compose -f docker-compose.prod.yml build --pull
        printf '\033[43m\033[30m BOOT \033[0m \033[33mDeploying services\033[0m\n'
        docker compose -f docker-compose.prod.yml up -d --remove-orphans
        printf '\033[42m\033[30m  OK  \033[0m \033[32mDeployed\033[0m\n'
    fi

# Stop the production stack (--dev for local services)
down *args:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ "{{ args }}" == *--dev* ]]; then
        printf '\033[41m\033[30m STOP \033[0m \033[31mStopping services\033[0m\n'
        docker compose down
        printf '\033[42m\033[30m  OK  \033[0m \033[32mServices stopped\033[0m\n'
    else
        printf '\033[41m\033[30m STOP \033[0m \033[31mStopping production stack\033[0m\n'
        docker compose -f docker-compose.prod.yml down
        printf '\033[42m\033[30m  OK  \033[0m \033[32mProduction stack stopped\033[0m\n'
    fi

# Run the bot and the website together with debug logs (starts services first, Ctrl-C stops both apps)
dev:
    @docker compose up -d --wait
    @pnpm run dev

# Lint, format and type-check the code
check:
    @uv --directory apps/bot run ruff check --fix src
    @uv --directory apps/bot run ruff format src
    @pnpm run format
    @pnpm --dir apps/web exec eslint --fix .
    @pnpm run check

# ── Database ──────────────────────────────────────────────────────────────────

[private]
db-ensure-init:
    -@DB_HOST=127.0.0.1 uv --directory apps/bot run aerich init-db > /dev/null 2>&1

# Generate a new migration from schema changes
db-migrate name="auto": db-ensure-init
    @printf '\033[43m\033[30m  DB  \033[0m \033[33mGenerating migration: {{ name }}\033[0m\n'
    @DB_HOST=127.0.0.1 uv --directory apps/bot run aerich migrate --name {{ name }}
    @printf '\033[42m\033[30m  OK  \033[0m \033[32mMigration created\033[0m\n'

# Apply all pending migrations
db-upgrade: db-ensure-init
    @printf '\033[43m\033[30m  DB  \033[0m \033[33mApplying migrations\033[0m\n'
    @DB_HOST=127.0.0.1 uv --directory apps/bot run aerich upgrade
    @printf '\033[42m\033[30m  OK  \033[0m \033[32mDatabase up to date\033[0m\n'

# Roll back the last applied migration
db-downgrade: db-ensure-init
    @printf '\033[41m\033[30m  DB  \033[0m \033[31mRolling back last migration\033[0m\n'
    @DB_HOST=127.0.0.1 uv --directory apps/bot run aerich downgrade -v -1
    @printf '\033[42m\033[30m  OK  \033[0m \033[32mRolled back\033[0m\n'

# Show applied migration history
db-history: db-ensure-init
    @DB_HOST=127.0.0.1 uv --directory apps/bot run aerich history

# Show migrations not yet applied
db-heads: db-ensure-init
    @DB_HOST=127.0.0.1 uv --directory apps/bot run aerich heads
