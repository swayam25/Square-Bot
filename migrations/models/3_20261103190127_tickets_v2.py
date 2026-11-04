from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "ticket" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "number" INT NOT NULL,
    "channel_id" BIGINT NOT NULL UNIQUE,
    "opener_id" BIGINT NOT NULL,
    "reason" TEXT NOT NULL,
    "status" VARCHAR(8) NOT NULL,
    "claimed_by" BIGINT,
    "closed_by" BIGINT,
    "control_message_id" BIGINT,
    "log_message_id" BIGINT,
    "created_at" TIMESTAMPTZ NOT NULL,
    "closed_at" TIMESTAMPTZ,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_ticket_guild_i_633552" UNIQUE ("guild_id", "number")
);
COMMENT ON TABLE "ticket" IS 'One row per ticket, numbered per guild, so nothing depends on channel names.';
        CREATE TABLE IF NOT EXISTS "ticket_member" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "added_by" BIGINT NOT NULL,
    "ticket_id" INT NOT NULL REFERENCES "ticket" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_ticket_memb_ticket__bea6a8" UNIQUE ("ticket_id", "user_id")
);
COMMENT ON TABLE "ticket_member" IS 'Members added to a ticket besides its opener.';
        ALTER TABLE "guild" ADD "ticket_confirm_close" BOOL NOT NULL DEFAULT True;
        ALTER TABLE "guild" ADD "ticket_support_role_ids" JSONB NOT NULL DEFAULT '[]';
        ALTER TABLE "guild" ADD "ticket_panel_channel_id" BIGINT;
        ALTER TABLE "guild" ADD "ticket_next_number" INT NOT NULL DEFAULT 1;
        ALTER TABLE "guild" ADD "ticket_category_id" BIGINT;
        ALTER TABLE "guild" ADD "ticket_max_open" INT NOT NULL DEFAULT 1;
        ALTER TABLE "guild" ADD "ticket_panel_message_id" BIGINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild" DROP COLUMN "ticket_confirm_close";
        ALTER TABLE "guild" DROP COLUMN "ticket_support_role_ids";
        ALTER TABLE "guild" DROP COLUMN "ticket_panel_channel_id";
        ALTER TABLE "guild" DROP COLUMN "ticket_next_number";
        ALTER TABLE "guild" DROP COLUMN "ticket_category_id";
        ALTER TABLE "guild" DROP COLUMN "ticket_max_open";
        ALTER TABLE "guild" DROP COLUMN "ticket_panel_message_id";
        DROP TABLE IF EXISTS "ticket";
        DROP TABLE IF EXISTS "ticket_member";"""


MODELS_STATE = (
    "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"
)
