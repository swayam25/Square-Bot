from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "giveaway" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "status" VARCHAR(10) NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "message_id" BIGINT UNIQUE,
    "host_id" BIGINT NOT NULL,
    "prize" VARCHAR(256) NOT NULL,
    "description" TEXT NOT NULL,
    "winner_count" INT NOT NULL,
    "starts_at" TIMESTAMPTZ NOT NULL,
    "ends_at" TIMESTAMPTZ NOT NULL,
    "ended_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL,
    "required_role_ids" JSONB NOT NULL,
    "require_all_roles" BOOL NOT NULL,
    "blocked_role_ids" JSONB NOT NULL,
    "min_account_days" INT NOT NULL,
    "min_member_days" INT NOT NULL,
    "min_invites" INT NOT NULL,
    "bonus_roles" JSONB NOT NULL,
    "ping_role_id" BIGINT,
    "winner_role_id" BIGINT,
    "color" VARCHAR(7),
    "image_url" TEXT,
    "image_file" VARCHAR(64),
    "button_label" VARCHAR(40) NOT NULL,
    "button_emoji" VARCHAR(100),
    "button_style" VARCHAR(8) NOT NULL,
    "entry_count" INT NOT NULL,
    "winner_ids" JSONB NOT NULL,
    "drawn_ids" JSONB NOT NULL,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_giveaway_guild_i_9bd60d" ON "giveaway" ("guild_id", "status");
CREATE INDEX IF NOT EXISTS "idx_giveaway_status_ac07f2" ON "giveaway" ("status", "starts_at");
CREATE INDEX IF NOT EXISTS "idx_giveaway_status_c8cea3" ON "giveaway" ("status", "ends_at");
        CREATE TABLE IF NOT EXISTS "giveaway_entry" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "bonus" INT NOT NULL,
    "entered_at" TIMESTAMPTZ NOT NULL,
    "giveaway_id" INT NOT NULL REFERENCES "giveaway" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_giveaway_en_giveawa_e3f396" UNIQUE ("giveaway_id", "user_id")
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "giveaway";
        DROP TABLE IF EXISTS "giveaway_entry";"""


MODELS_STATE = (
    "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"
)
