#!/bin/sh
# Reads the central config.toml and exports the values Caddy needs:
#   [domains].drizzle -> DRIZZLE_DOMAIN
#   [domains].dozzle  -> DOZZLE_DOMAIN
#   auth-pass         -> CADDY_AUTH_HASH (bcrypt-hashed for basic auth)
# Keeping this here means config.toml stays the single source of truth.
set -e

CONFIG="${SQUARE_CONFIG:-/square/config.toml}"

# toml_get <section> <key>  — pass "" as <section> for root-level keys.
toml_get() {
	awk -F'"' -v section="[$1]" -v key="$2" '
		/^[ \t]*\[/ { cur = $0; next }
		{
			want = (section == "[]") ? (cur == "") : (cur == section)
			if (want && $1 ~ ("^[ \t]*" key "[ \t]*=")) { print $2; exit }
		}
	' "$CONFIG"
}

AUTH_PASS="$(toml_get '' auth-pass)"

if [ -z "$AUTH_PASS" ]; then
	echo "[caddy-entrypoint] 'auth-pass' is empty in $CONFIG — set it to enable web auth." >&2
	exit 1
fi

# Only export a domain when it's set. Caddy applies the port fallback in the
# Caddyfile (e.g. {$DRIZZLE_DOMAIN::8080}) only when the var is *unset* — an
# exported-but-empty var would resolve to an empty address and break parsing.
DRIZZLE_DOMAIN="$(toml_get domains drizzle)"
DOZZLE_DOMAIN="$(toml_get domains dozzle)"
[ -n "$DRIZZLE_DOMAIN" ] && export DRIZZLE_DOMAIN || unset DRIZZLE_DOMAIN
[ -n "$DOZZLE_DOMAIN" ] && export DOZZLE_DOMAIN || unset DOZZLE_DOMAIN

export CADDY_AUTH_HASH="$(caddy hash-password --plaintext "$AUTH_PASS")"

exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
