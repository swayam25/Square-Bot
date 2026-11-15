from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "ticket_file";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
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
COMMENT ON TABLE "ticket_file" IS 'A copy of a ticket''s picture, since Discord''s attachment links stop working after about a day.';"""


MODELS_STATE = (
    "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"
    "jaus7n2TEVSbVLUu2VSMKqzuzpf4Myb7Q="
)
