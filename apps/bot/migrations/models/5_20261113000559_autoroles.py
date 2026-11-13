from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "autorole_user" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "role_ids" JSONB NOT NULL,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_autorole_us_guild_i_c5b492" UNIQUE ("guild_id", "user_id")
);
        ALTER TABLE "guild" ADD "autorole_split" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "guild" ADD "autorole_ids" JSONB NOT NULL DEFAULT '[]';
        ALTER TABLE "guild" ADD "autorole_bot_ids" JSONB NOT NULL DEFAULT '[]';
        UPDATE "guild" SET "autorole_ids" = jsonb_build_array("autorole") WHERE "autorole" IS NOT NULL;
        ALTER TABLE "guild" ALTER COLUMN "autorole_ids" DROP DEFAULT;
        ALTER TABLE "guild" ALTER COLUMN "autorole_bot_ids" DROP DEFAULT;
        ALTER TABLE "guild" DROP COLUMN "autorole";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild" ADD "autorole" BIGINT;
        UPDATE "guild" SET "autorole" = ("autorole_ids"->>0)::BIGINT;
        ALTER TABLE "guild" DROP COLUMN "autorole_split";
        ALTER TABLE "guild" DROP COLUMN "autorole_ids";
        ALTER TABLE "guild" DROP COLUMN "autorole_bot_ids";
        DROP TABLE IF EXISTS "autorole_user";"""


MODELS_STATE = (
    "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"
)
