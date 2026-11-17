from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "starboard" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "channel_id" BIGINT NOT NULL,
    "enabled" BOOL NOT NULL,
    "emojis" JSONB NOT NULL,
    "downvote_emojis" JSONB NOT NULL,
    "threshold" INT NOT NULL,
    "drop_below" INT,
    "self_vote" BOOL NOT NULL,
    "allow_bots" BOOL NOT NULL,
    "channel_mode" VARCHAR(8) NOT NULL,
    "channel_ids" JSONB NOT NULL,
    "blocked_role_ids" JSONB NOT NULL,
    "max_age_days" INT,
    "follow_deletes" BOOL NOT NULL,
    "color" VARCHAR(7),
    "created_at" TIMESTAMPTZ NOT NULL,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_starboard_guild_i_2ea7f8" UNIQUE ("guild_id", "channel_id")
);
        CREATE TABLE IF NOT EXISTS "starboard_post" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "message_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "author_id" BIGINT NOT NULL,
    "post_id" BIGINT UNIQUE,
    "webhook_id" BIGINT,
    "score" INT NOT NULL,
    "emoji" VARCHAR(64),
    "forced" BOOL NOT NULL,
    "uploaded" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "board_id" INT NOT NULL REFERENCES "starboard" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_starboard_p_board_i_5d1f5a" UNIQUE ("board_id", "message_id")
);
CREATE INDEX IF NOT EXISTS "idx_starboard_p_board_i_17a0ba" ON "starboard_post" ("board_id", "score");
CREATE INDEX IF NOT EXISTS "idx_starboard_p_board_i_732920" ON "starboard_post" ("board_id", "author_id");
CREATE INDEX IF NOT EXISTS "idx_starboard_p_message_cb4090" ON "starboard_post" ("message_id");
        CREATE TABLE IF NOT EXISTS "starboard_vote" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "message_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "emoji" VARCHAR(32) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_starboard_v_message_876218" UNIQUE ("message_id", "user_id", "emoji")
);
CREATE INDEX IF NOT EXISTS "idx_starboard_v_channel_14ad19" ON "starboard_vote" ("channel_id");
CREATE INDEX IF NOT EXISTS "idx_starboard_v_created_a8fa83" ON "starboard_vote" ("created_at");
COMMENT ON TABLE "starboard_vote" IS 'Reactions with a board emoji, bots included, so the stored count matches Discord''s and drift shows.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "starboard_post";
        DROP TABLE IF EXISTS "starboard_vote";
        DROP TABLE IF EXISTS "starboard";"""


MODELS_STATE = (
    "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"
    "UhI2FWY//g/pd7Z9"
)
