from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "ticket_file" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "attachment_id" BIGINT NOT NULL,
    "content_type" VARCHAR(32) NOT NULL,
    "size" INT NOT NULL,
    "data" BYTEA NOT NULL,
    "ticket_id" INT NOT NULL REFERENCES "ticket" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_ticket_file_ticket__a2bc09" UNIQUE ("ticket_id", "attachment_id")
);
COMMENT ON TABLE "ticket_file" IS 'A copy of a ticket''s picture, since Discord''s attachment links stop working after about a day.';
        CREATE TABLE IF NOT EXISTS "ticket_transcript" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "data" JSONB NOT NULL,
    "saved_at" TIMESTAMPTZ NOT NULL,
    "ticket_id" INT NOT NULL UNIQUE REFERENCES "ticket" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "ticket_transcript" IS 'Kept apart from the ticket row so listing tickets never loads their messages.';
        ALTER TABLE "ticket" ADD "participant_ids" JSONB NOT NULL DEFAULT '[]';
        ALTER TABLE "ticket" ALTER COLUMN "participant_ids" DROP DEFAULT;
        ALTER TABLE "ticket" ADD "message_count" INT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "ticket" DROP COLUMN "participant_ids";
        ALTER TABLE "ticket" DROP COLUMN "message_count";
        DROP TABLE IF EXISTS "ticket_file";
        DROP TABLE IF EXISTS "ticket_transcript";"""


MODELS_STATE = (
    "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"
)
