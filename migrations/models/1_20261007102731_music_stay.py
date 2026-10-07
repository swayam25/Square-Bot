from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild" ADD "music_stay_channel_id" BIGINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild" DROP COLUMN "music_stay_channel_id";"""


MODELS_STATE = (
    "eJztmm1z2jgQgP+Kxp/oTC6TmCTk7hsQ0pIm0CHcy7TT0QhbMUpsiVpyUqaX/36S8Ds2B4"
    "QkwPgbXu1K8rPS7iL5l+ExG7v88OJqwFw8RCMXG3+AXwZFnvpR1HwADDSZJI1KIEJDw76H"
    "PguVRlz4yBJSfIdcjqXIxtzyyUQQRpVyn2LgsycwwT6oOQFx7QOgrD+ACSL+AXAJF4Q6QI"
    "yxlnP5CwlgsYAKgDi4uOKHaiSbWXIoqbnJTgNKfgQYCuZgqerLrr99M3R/qlVZQmIb37/L"
    "B0Jt/BNzpaIeJw/wjmCplwZJtJmWQzGdaFmXikutqN5hBC3mBh5NlCdTMWY01iZUKKmDKf"
    "aRwKp74QcKKw1cN3RARHo2+0RlNsWUjY3vUOAq5yjr2QQSmQFhrz+Et50hhMac4yKLFPZQ"
    "ZDGqnC6nyvXbO2oKv5nHJ42T8/rZyblU0dOMJY3n2dAJmJmhxtMbGs+6HQk009CME6iRF+"
    "bItohTCjdl9P+EI56LEEeChHGy3t8O8u+mWa83zKP62fnpSaNxen4U055vWoS91f2oyEsF"
    "JrfvbFtHrkjQ651QyL4UfNpkn8i/aHmrgHH3ULi642CT5XvJfEwc+hlPNeaunBKiFi6gGg"
    "bvj6qfOHbvGOPnaBVF0iSE+egpDrSZxSURyBfHQkNoN2/bzYuOoUmPkPXwhHwbZpCrFmay"
    "nCTWnW/yTC8vQRQ5mo56DTXpKHPix/KsGrUtTqn4cal0Wo60IJVVaesd01bAsb9y2koZbS"
    "Z4bgPiN05a94xQbEMk5tFfSHKCeLgYfsYwh98OLQ+jHzsYZQ0fI7tP3Wm4DBaQHnZvOrfD"
    "5s0XNZzH+Q9X42sOO6rF1NJpTlo7+5B1TdwJ+Ls7/ATUI/ja73U0XsaF4+sRE73hV0PNCQ"
    "WCQcqeILJTKzaSRtTmk+r7xP5U4i2I/tm0XB7/4zKgygB7kwHKq+dFKWDzBfQ2QH7jHCCI"
    "9YAFtDybF9Bn8s8hosX4c5Y5D4yk6WtF/ljyegV2IdB+/zoT5VvdHN7enzetzqB2rMO7VC"
    "KihLqHbYIgkxkGWmNEKXZXXv2lXay1FcKFvjUJ+F32gkqc0XHd8o5IW1Xs12Vv30OV7FeM"
    "QSmrKv6sEn8CTqz1Q0+BdbXy1135M5oe5lyWzWv6Imtd+eJlvuACvSAvl3VReWUVr6zwnz"
    "WTRPQdVoHHQsvLzwPsIv3a8y4pvt3bsbOLshPizDp3mROtzhfCumZOe9bR3gF7zbOQPLaC"
    "A5ECsuWnIimHrn/ZLDsByr3R3bAnx1N3w0i3WNKlDvOnQDBABAfhcMtdOa/f9eKLZ/Xeek"
    "VWN8/veYATu2EOrVzCfjHbtE2OsJz6DgYSudt/QhdTR4zlY91cQPSv5qD9qTmo1c3cSXAv"
    "bDF1U7Y4Wbci2UAZsnWoq0v+6pK/uuTf0kv+JvaJNS6qacKWhaUMSnSqG55d2taLCoRH7P"
    "Pwf8Sy9UHKZA/LA/P0dIn6QGqVFgi6LXeALTfVCoRD9T2ke3x0tARdqVVKV7fl6i9GBaYF"
    "H0tc3fZ7JaVXYpL/TIJYAvyrP7/dQdoL4CoYmVPqiGntpvlPHnf7ut/ScFIfOagOWqudAG"
    "0+mT3/B6ekoDA="
)
