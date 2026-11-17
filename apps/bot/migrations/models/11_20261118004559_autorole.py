from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "sticky_role" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "role_ids" JSONB NOT NULL,
    "saved_at" TIMESTAMPTZ NOT NULL,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_sticky_role_guild_i_1e73b8" UNIQUE ("guild_id", "user_id")
);
COMMENT ON TABLE "sticky_role" IS 'The roles someone had when they left, kept until they rejoin while sticky roles are on.';
        ALTER TABLE "guild" ADD "autorole_delay" INT NOT NULL DEFAULT 0;
        ALTER TABLE "guild" ADD "autorole_sticky_ignore_ids" JSONB NOT NULL DEFAULT '[]'::jsonb;
        ALTER TABLE "guild" ADD "autorole_screening" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "guild" ADD "autorole_sticky" BOOL NOT NULL DEFAULT False;
        UPDATE "guild" SET "modules" = "modules" || '["autorole"]'::jsonb WHERE NOT "modules" @> '["autorole"]'::jsonb;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        UPDATE "guild" SET "modules" = "modules" - 'autorole';
        ALTER TABLE "guild" DROP COLUMN "autorole_delay";
        ALTER TABLE "guild" DROP COLUMN "autorole_sticky_ignore_ids";
        ALTER TABLE "guild" DROP COLUMN "autorole_screening";
        ALTER TABLE "guild" DROP COLUMN "autorole_sticky";
        DROP TABLE IF EXISTS "sticky_role";"""


MODELS_STATE = (
    "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"
)
