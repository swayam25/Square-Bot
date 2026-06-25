set shell := ["bash", "-euo", "pipefail", "-c"]

[private]
default:
    @just --list --list-heading $'\n\033[1;96mSquare\033[0m \033[2m/ Available Commands\033[0m\n' --list-prefix $'  \033[36m›\033[0m '

# Sync dependencies and install hooks
setup:
    @printf '\033[43m\033[30m SYNC \033[0m \033[33mSyncing Dependencies\033[0m\n'
    @uv sync
    @printf '\033[43m\033[30m HOOK \033[0m \033[33mInstalling Pre Commit\033[0m\n'
    @uv run pre-commit install
    @printf '\033[42m\033[30m  OK  \033[0m \033[32mDone\033[0m\n'

# Start local docker services
start:
    #!/usr/bin/env bash
    set -euo pipefail
    printf '\033[43m\033[30m INFO \033[0m \033[33mStarting services\033[0m\n'
    docker compose up db drizzle-gateway caddy -d --build
    url=$(docker inspect -f '{{{{with index .NetworkSettings.Ports "80/tcp"}}http://localhost:{{{{(index . 0).HostPort}}{{{{end}}' square_caddy)
    printf '\033[42m\033[30m  OK  \033[0m \033[32mServices ready\033[0m\n'
    printf '\033[46m\033[30m LINK \033[0m \033[36mDatabase panel → %s\033[0m\n' "$url"

# Stop local docker services
stop:
    @printf '\033[41m\033[30m STOP \033[0m \033[31mStopping services\033[0m\n'
    @docker compose down

# Run the bot locally (auto-starts services if not running)
dev:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ $(docker compose ps --status running -q db drizzle-gateway caddy 2>/dev/null | wc -l) -lt 3 ]]; then
        just start
    fi
    printf '\n'
    DB_HOST=localhost uv run main.py

# ── Database ──────────────────────────────────────────────────────────────────

# Generate a new migration from schema changes
db-migrate name="auto":
    @printf '\033[43m\033[30m  DB  \033[0m \033[33mGenerating migration: {{name}}\033[0m\n'
    @DB_HOST=localhost uv run aerich migrate --name {{name}}
    @printf '\033[42m\033[30m  OK  \033[0m \033[32mMigration created\033[0m\n'

# Apply all pending migrations
db-upgrade:
    @printf '\033[43m\033[30m  DB  \033[0m \033[33mApplying migrations\033[0m\n'
    @DB_HOST=localhost uv run aerich upgrade
    @printf '\033[42m\033[30m  OK  \033[0m \033[32mDatabase up to date\033[0m\n'

# Roll back the last applied migration
db-downgrade:
    @printf '\033[41m\033[30m  DB  \033[0m \033[31mRolling back last migration\033[0m\n'
    @DB_HOST=localhost uv run aerich downgrade -v -1
    @printf '\033[42m\033[30m  OK  \033[0m \033[32mRolled back\033[0m\n'

# Show applied migration history
db-history:
    @DB_HOST=localhost uv run aerich history

# Show migrations not yet applied
db-heads:
    @DB_HOST=localhost uv run aerich heads

# ── Deploy ────────────────────────────────────────────────────────────────────

# Pull latest, rebuild, and deploy
prod:
    @printf '\033[43m\033[30m PULL \033[0m \033[33mPulling latest\033[0m\n'
    @git pull
    @printf '\033[43m\033[30m BLD  \033[0m \033[33mRebuilding images\033[0m\n'
    @docker compose build --pull
    @printf '\033[43m\033[30m BOOT \033[0m \033[33mDeploying services\033[0m\n'
    @docker compose up -d --remove-orphans
    @printf '\033[42m\033[30m  OK  \033[0m \033[32mDeployed\033[0m\n'
