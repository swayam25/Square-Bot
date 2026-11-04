from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "invite_bonus" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "amount" INT NOT NULL,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_invite_bonu_guild_i_973f83" UNIQUE ("guild_id", "user_id")
);
COMMENT ON TABLE "invite_bonus" IS 'One row per (guild, user), bonus invites granted by moderators.';
        CREATE TABLE IF NOT EXISTS "invite_join" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "member_id" BIGINT NOT NULL,
    "inviter_id" BIGINT,
    "code" VARCHAR(32),
    "joined_at" TIMESTAMPTZ NOT NULL,
    "left_at" TIMESTAMPTZ,
    "fake" BOOL NOT NULL,
    "guild_id" INT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_invite_join_guild_i_330567" UNIQUE ("guild_id", "member_id")
);
CREATE INDEX IF NOT EXISTS "idx_invite_join_guild_i_5d0a43" ON "invite_join" ("guild_id", "inviter_id");
COMMENT ON TABLE "invite_join" IS 'One row per (guild, member): who invited them, through which code, and whether they''re still here.';
        ALTER TABLE "guild" ADD "invite_fake_days" INT NOT NULL DEFAULT 7;
        ALTER TABLE "guild" ADD "invite_tracker" BOOL NOT NULL DEFAULT False;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild" DROP COLUMN "invite_fake_days";
        ALTER TABLE "guild" DROP COLUMN "invite_tracker";
        DROP TABLE IF EXISTS "invite_bonus";
        DROP TABLE IF EXISTS "invite_join";"""


MODELS_STATE = (
    "eJztXG1T4joU/iuZfrk6w3UUVLz7DRB3cRXuKPdldmenE9pQIm3Ctqkus9f/fpPQ0hdSpB"
    "UR2H5x6Mk5Sfqc5Lwkp/7UHGoi2zu6vL6jNurDgY20D+CnRqAjfqiaK0CDk0nUKAgsENTM"
    "B92lAdPAYy40GCcPoe0hTjKRZ7h4wjAlgrlHEHDpE5ggFxxYPrbNChDSh2ACsVsBNvYYJh"
    "ZgIyTpHv8FGTCoTxiAHri89o7ESCY1+FCcc52d+gR/95HOqIU4q8u7/vpVk/2JViGpY1P7"
    "9o0/YGKiH8gTLOJxMtaHGHG+OJBYikm6zqYTSesQdiUZxTsMdIPavkMi5smUjSiZc2PCBN"
    "VCBLmQIdE9c30BK/FtO1BAiPRs9hHLbIoxGRMNoW8L5Qjp2QQimqbr3V5fv2/3dV1bUFwo"
    "EYM9IBmUCKXzqXry7S0xhd+rJ6f104va+ekFZ5HTnFPqz7OhI2BmghKebl97lu2QwRmHxD"
    "gCNdTCArJNbGWCGxN6GeEQz2UQh4QI42i9bw7kP6rVWq1ePa6dX5yd1utnF8dztBeblsHe"
    "7HwUyHMGyrfvbFuHqoiglztBiX0m8HGRfUL+VctbGIzhWLm658Ymie8VdRG2yGc0lTB3+J"
    "QgMZAC1cB4fxT9zG33jmH8HK6ikBqZMBc+zQ1tYnFxCPiLIyZBaDXuW43LtiaRHkBj/ARd"
    "U09ALlpolaYoc97FJqfqpCmQQEuiI15DTDr0nOgx26uGbctdKnpcyZ1mQ6pwZaXbeke35X"
    "vIze22YkLrMZ7bAPGGndYDxQSZOmSL0F9y5Bh2kBr8hGAKfjOQPAp/7KCV1VwEzR6xp8Ey"
    "WIJ0v3Pbvu83bv8Uwzme992W8DX6bdFSldRpinpwfphUzbwT8E+n/wmIR/Cl121LeKnHLF"
    "eOGPH1v2hiTtBnVCf0SYdmbMWG1BC1Raf6PrY/5ngV1j/plrPt/zwMKD3A3niA7Oh5mQtY"
    "fwC9DSBv2AcwbIwR0w3H9BToU54cQqKGPyWZ0sCAi76V5Z9T3i7AVgLa690krHyzk4K3+9"
    "dts313cCLNO2fCLAN1B5kY6pR7GN0YQUKQnXv1Z3ZRaCsEC31rHPC77AXhOMPjutUVEZcq"
    "sS+KvfmgC2ef0wbFpEr7k8f++B42ipsehXS58ouu/BmaDvI8HjYX1EVSutTF63ThMfgKv5"
    "zVRamVolrB5JFbMl1ke2OereVzEYvCpafI4SkC+IZwjHQTThVJQnb2qxDd3EVH/W23wHpv"
    "ObIPZBIRkrygVaz/QPLq8x2yoXyhRajVV9c7djCXdf2hWrIDSnzvtXB1ZF9N0dWvgJk42F"
    "0LYte8o70GzKZW6N9fCdgNtVqzjvYOsLc8TV7YmYozZdXuzT5ZjtuNlQ6YlcU14mLqsAJk"
    "L2DWpQcsFxKuTjCYAjEw1y11VyzWydnf8jqd8NasrNMpLzx/yVQCOqKwLceajgQ2h/rxVq"
    "/rsuipLHrajviisiNFT+mQODNSSUTNLwYqIlgvHqc4yBnwyOIDeBrRIK4wRRWwU+F/Xepb"
    "I96CjREw+AQqABKTP8uYQnBNf3MR8Bi2bcApaLVQZv1DLo92ZuOp4p0Y02weEVcZBm0qDI"
    "rUkysQSojtkw95l1PV/Pgn5cpT7aL4G8rrztYIumrcDfVFJ3+RHUTcgT90GxGLjfhjrboE"
    "zL8bd61PjbuDWjVVNNcNWqqyqaxszBNKbXslY4jJQilj4ggODVkBFcfE1qDgLdtY+6RfcX"
    "GU87IvFCmv+HJc8ZVpfJnGl2n8y2l8+qJGkcYr7nKy0/jYFVLxNJ53AsQiCb/ndfh44nte"
    "KFsMvjos6k4B4wk380Aw3GrpevGul6fl4r3lui5vId4z/Z6rIUcOEpcplIdsm01660SkaB"
    "XZGkrHtg7q8sPsMrgpg5stDW4ayMXGSBXTBC1LQxkY8ZRf5e3Stl4WIDwi1wsql1aND2Ii"
    "exgeVM/OVogPOFdmgCDbUhUJfFPlQDhg30N0T46PV0CXc2WiK9vSh+yEIVXBx/V9r5t1zj"
    "4XSZ8PYoOB/+S/TNpBtJeAK8BIHCaFmB7cNv5Nw9266TXTx32ig2a+wub1O7Pn/wFOzyR9"
)
