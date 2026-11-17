from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "automod_rule" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "kind" VARCHAR(16) NOT NULL,
    "enabled" BOOL NOT NULL,
    "amount" INT,
    "seconds" INT,
    "channel_ids" JSONB NOT NULL,
    "delete_message" BOOL NOT NULL,
    "warn" BOOL NOT NULL,
    "notify" BOOL NOT NULL,
    "exempt_role_ids" JSONB NOT NULL,
    "exempt_channel_ids" JSONB NOT NULL,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_automod_rul_guild_i_1203d4" UNIQUE ("guild_id", "kind")
);
        CREATE TABLE IF NOT EXISTS "warn_punishment" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "warnings" INT NOT NULL,
    "action" VARCHAR(8) NOT NULL,
    "seconds" INT,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_warn_punish_guild_i_f5460a" UNIQUE ("guild_id", "warnings")
);
        CREATE TABLE IF NOT EXISTS "warning" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "moderator_id" BIGINT,
    "reason" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_warning_guild_i_711e40" ON "warning" ("guild_id", "user_id");
        INSERT INTO "automod_rule" ("guild_id", "kind", "enabled", "channel_ids", "delete_message", "warn", "notify", "exempt_role_ids", "exempt_channel_ids")
SELECT "id", 'media', TRUE, jsonb_build_array("media_only_channel_id"), TRUE, FALSE, TRUE, '[]'::jsonb, '[]'::jsonb FROM "guild" WHERE "media_only_channel_id" IS NOT NULL;
        ALTER TABLE "guild" DROP COLUMN "media_only_channel_id";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild" ADD "media_only_channel_id" BIGINT;
        UPDATE "guild" SET "media_only_channel_id" = ("automod_rule"."channel_ids"->>0)::BIGINT FROM "automod_rule" WHERE "automod_rule"."guild_id" = "guild"."id" AND "automod_rule"."kind" = 'media' AND jsonb_array_length("automod_rule"."channel_ids") > 0;
        DROP TABLE IF EXISTS "automod_rule";
        DROP TABLE IF EXISTS "warning";
        DROP TABLE IF EXISTS "warn_punishment";"""


MODELS_STATE = (
    "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"
)
