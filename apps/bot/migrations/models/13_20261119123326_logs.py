from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild" ADD "log_ignored_channel_ids" JSONB NOT NULL DEFAULT '[]';
        ALTER TABLE "guild" ADD "log_ignored_role_ids" JSONB NOT NULL DEFAULT '[]';
        ALTER TABLE "guild" ADD "log_skip_bots" BOOL NOT NULL DEFAULT True;
        ALTER TABLE "guild" ADD "log_disabled_events" JSONB NOT NULL DEFAULT '[]';
        INSERT INTO "log_channel" ("guild_id", "log_type", "channel_id")
            SELECT DISTINCT ON ("guild_id") "guild_id", 'server', "channel_id" FROM "log_channel"
            WHERE "log_type" IN ('channels', 'roles', 'invites')
                AND "guild_id" NOT IN (SELECT "guild_id" FROM "log_channel" WHERE "log_type" = 'server')
            ORDER BY "guild_id", array_position(ARRAY['channels', 'roles', 'invites'], "log_type"::text);
        DELETE FROM "log_channel" WHERE "log_type" IN ('channels', 'roles', 'invites');"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild" DROP COLUMN "log_ignored_channel_ids";
        ALTER TABLE "guild" DROP COLUMN "log_ignored_role_ids";
        ALTER TABLE "guild" DROP COLUMN "log_skip_bots";
        ALTER TABLE "guild" DROP COLUMN "log_disabled_events";"""


MODELS_STATE = (
    "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"
    "Yael1V0nsy//Bzd+sP4="
)
