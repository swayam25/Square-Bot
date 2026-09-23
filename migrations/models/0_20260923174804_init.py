from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "dev" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL UNIQUE,
    "joined_at" TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS "guild" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL UNIQUE,
    "ticket_cmds" BOOL NOT NULL,
    "media_only_channel_id" BIGINT,
    "autorole" BIGINT,
    "dj_mode" BOOL NOT NULL,
    "music_channel_id" BIGINT,
    "music_message_id" BIGINT
);
CREATE TABLE IF NOT EXISTS "dj_role" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "role_id" BIGINT NOT NULL,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_dj_role_guild_i_f8bc91" UNIQUE ("guild_id", "role_id")
);
COMMENT ON TABLE "dj_role" IS 'One row per (guild, role) pair, listing the roles that count as DJs.';
CREATE TABLE IF NOT EXISTS "log_channel" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "log_type" VARCHAR(32) NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_log_channel_guild_i_2ef505" UNIQUE ("guild_id", "log_type")
);
COMMENT ON TABLE "log_channel" IS 'One row per (guild, log type) pair, mapping a log category to its channel.';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztmltz2joQgP+Kxk90JieTmCTk9A0IaUkT6BDOZdrpaIStGCW2RC05KdOT/15J+I7NAU"
    "oSYPyGV7uy/K20u/by0/CYjV1+eHE1YC4eopGLjffgp0GRp34UDR8AA00myaASiNDQsO+h"
    "z0KlERc+soQU3yGXYymyMbd8MhGEUaXcpxj47AlMsA9qTkBc+wAo63dggoh/AFzCBaEOEG"
    "Os5Vz+QgJYLKACIA4urvihupPNLHkrqbnJSQNKvgcYCuZgqerLqb9+NfR8alRZQmIb377J"
    "C0Jt/ANzpaIuJw/wjmCplwZJtJmWQzGdaFmXikutqJ5hBC3mBh5NlCdTMWY01iZUKKmDKf"
    "aRwGp64QcKKw1cN3RARHq2+kRltsSUjY3vUOAq5yjr2QISmQFhrz+Et50hhMac4yKLFPZQ"
    "ZDGqnC6XyvXTO2oJf5jHJ42T8/rZyblU0cuMJY3n2a0TMDNDjac3NJ71OBJopqEZJ1AjL8"
    "yRbRGnFG7K6P8JRzwXIY4ECeNkv78e5D9Ns15vmEf1s/PTk0bj9Pwopj0/tAh7q/tBkZcK"
    "TB7f2bGOXJGg1yehkH0p+LTJPpH/re2tAsbdQ+HujoNNlu8l8zFx6Cc81Zi7ckmIWriAah"
    "i8P6h54ti9Y4yfo10USZMQ5qOnONBmNpdEIB8cCw2h3bxtNy86hiY9QtbDE/JtmEGuRpjJ"
    "cpJYd37IM728BFHkaDrqMdSio8yJH8uzajS2OKXix6XSaTnSglRWpa03TFsBx/7KaStltJ"
    "nguQ2IXzlp3TNCsQ2RmEd/IckJ4uFi+BnDHH47tDyMfuxglDV8jOw+dafhNlhAeti96dwO"
    "mzef1e08zr+7Gl9z2FEjppZOc9La2busa+JJwD/d4UegLsGXfq+j8TIuHF/fMdEbfjHUml"
    "AgGKTsCSI7tWMjaURtPqm+TexPJd6C6J9Ny+XxPy4DqgywNxmgvHpelAI2X0BvA+RXzgGC"
    "WA9YQMuzeQF9Jl8OES3Gn7PMeWAkTV8q8seSlyuwC4H2+9eZKN/q5vD2/rppdQa1Yx3epR"
    "IRJdQ9bBMEmcww0BojSrG78u4vnWKtoxBu9K1JwG9yFlTijD7XLe+ItFXFfl329j1UyX7F"
    "GJSyquLPKvEn4MRaP/QUWFc7f92dP6PpYc5l2bymL7LWlS9W8cUKb0eZcKW7JQXOCi0vPw"
    "2wi/Rjz7ukuI+0Y2/JZd8iM7vbZU4UKX4T1jVz2rOJ9g7YS75157EVvHoXkC1//045dP22"
    "ppwEKPdGXUhP3k91IZEesaRLHeZPgWCACA7C2y3X3Fx/6sUtTvXcekdWPc63/FQQu2EOrd"
    "zCfjHbtE2OsFz6DgYSedp/QBdTR4zlZd1cQPTv5qD9sTmo1c3cN8deOGLqoWxJsm5huIGS"
    "cOtQV+3kqp1ctZO3tJ3cxD6xxkU1TTiysJRBiU7VS9ilY72oQHjEPg/fI5atD1Ime1gemK"
    "enS9QHUqu0QNBjuU+l8lCtQDhU30O6x0dHS9CVWqV09Viu/mJUYFrQlr+67fdKSq/EJN+Q"
    "J5YA/+k/eu4g7QVwFYzM99CIae2m+W8ed/u638q309UErdW+AG0+mT3/As2iINA="
)
