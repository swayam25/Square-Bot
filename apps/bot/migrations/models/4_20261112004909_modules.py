from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    # Each server keeps what it had: tickets stay on where commands were on or a panel was posted
    return """
        ALTER TABLE "guild" ADD "modules" JSONB NOT NULL DEFAULT '["logs"]';
        UPDATE "guild" SET "modules" = '["logs"]'::jsonb
            || CASE WHEN "ticket_cmds" OR "ticket_panel_channel_id" IS NOT NULL
                THEN '["tickets"]'::jsonb ELSE '[]'::jsonb END
            || CASE WHEN "invite_tracker" THEN '["invites"]'::jsonb ELSE '[]'::jsonb END;
        ALTER TABLE "guild" ALTER COLUMN "modules" DROP DEFAULT;
        ALTER TABLE "guild" DROP COLUMN "ticket_cmds";
        ALTER TABLE "guild" DROP COLUMN "invite_tracker";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild" ADD "ticket_cmds" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "guild" ADD "invite_tracker" BOOL NOT NULL DEFAULT False;
        UPDATE "guild" SET "ticket_cmds" = "modules" ? 'tickets', "invite_tracker" = "modules" ? 'invites';
        ALTER TABLE "guild" DROP COLUMN "modules";"""


MODELS_STATE = (
    "eJztXe1P2zgY/1esfDmQeggKDG6aJvG2HQzoCXp306YpchPTZiR2lzhAteN/P9tJmjcnNO"
    "lbyPxlorYfJ/k99vNu76fmEBPZ3tbpxQ2xUR8ObKS9BT81DB3+h6y7AzQ4HsedvIGGhJr5"
    "XXdJOGjgURcalDXfQdtDrMlEnuFaY2oRzAf3MAIueQRj5IKNoW/ZZgdw6k0whpbbAbblUQ"
    "sPAR0h0e6xvyAFBvExBdADpxfeFn+SSQz2KDZykZP62PrhI52SIWJDXTb116+amI/3ckrd"
    "MrVv39gPC5voCXl8CP85vtfvLMTGJYG0BJlo1+lkLNrOMf0gBvJvGOgGsX0Hx4PHEzoieD"
    "rawpS3DhFGLqSIT09dn8OKfdsOGRAhHbx9PCR4xQSNie6gb3PmcOrgBeI2Tdeve3399qyv"
    "61qOcRFFAvawySCYM529qie+fshf4ffuzt7B3uHum71DNkS85rTl4Dl4dAxMQCjgue5rz6"
    "IfUhiMEBjHoEZcyCF7bA0LwU0QvYxwhGcZxFFDjHG83lcH8h/d7u7uQXd7983h/t7Bwf7h"
    "9hTtfFcZ7MfnHznybABh2zfY1hErYujFTpBiXwh8kqRNyM+1vLnAuLuXru6psEnj+4G4yB"
    "riT2giYD5nrwSxgSSohsL7I59nKrtfGcbP0SqKWmMR5sLHqaBNLS4GAftwRAUIJ0e3J0en"
    "Z5pAegCN+0fomnoKct5DuiTTMh2b73K6TrYFYjgU6PDP4C8daU70UKxVo75ylYoeZlKnxZ"
    "BKVJlSW2tUW76H3MpqK0G0GOHZBIhXrLS+EwsjU4c0D/0pQ45aDpKDnyLMwG+GlFvRH69Q"
    "ymougmYP25NwGZQg3T+/OrvtH139xR/neN4PW8B31D/jPV3ROsm0brzZTLNmOgn497z/J+"
    "A/wZfe9ZmAl3h06IonxuP6XzT+TtCnRMfkUYdmYsVGrRFqeaW6HtmfULwS6Z9Wy8Xyf2oG"
    "KA3QGg1QbD2XqYDFG9BNAHnFOoDtMJ95/XnkL25713LcEyRZ2W8ZFPwnYgrLkvrauzsfGx"
    "xb4P3wocv0zGDLM0bIgVvvbOgMTPj+vbZc61uGNocrpQKu/zm6Ofnz6Gbj6uhzRtxfn1z2"
    "jrOynU9wnGUOMi2oE6aIdGMEMUZ25U1SOEWtHRPuh8bo6bVsGa5fo6je7IxIUins62Jvft"
    "e5TSCBnjBsIZZjn6DKQD9gZMsSVdOW1Uqi417vMiWJjs8zsF7/fXV8drOxI8QSG2TRIuXg"
    "e5ZRX/RIqNXKr62oBZoO8jxmXdfkRZpa8WI+XngUzqGXi6ZQXKnLFQs/MEmm38F7pJtwIr"
    "Fpix01CenqYvIHy2XDnG5bDDC1jHtEdYN9/pC4k8prXk6vFnzdBR/i6fnjMXGpHmbyKvly"
    "JVOs1bcbMN+eWtjb4s9rjT8Xoj2GXNzX1Rwlk6itNOdWCkCta2SVTKI4MydnHPikkzHCFZ"
    "S6hHJ1On3nlel0gu8s19ENm3hVveuiKVboakdx2lfraYcYYvTE/vGdAXKrL/QMsVrr0oKS"
    "4txXKsokauEkGyGk/PDpBtlQfFAeanmV4CvLgRZVmshcrgHBvjcvXOdirmM+1a+AGc+hLw"
    "SxCzZRqwGzyTCyc+cE7JIMT4KJWg1YoA/mxKovJmkdTssscMhJMEmZg0zKFRc7JOWrGFmr"
    "iJzXSm12gJgFBFN6YOhCzNgJBhPAH8x4S9wZ68crzldeOh4VcqnScVWD90s6uNDhZy0qrO"
    "mYYHWobzd6Xas6fFWH3wz7ovNK6vCzrkOhpZLyLl40VLhTU99OcRCPXWy+BY8jEtoVJj+Y"
    "5nTYvy7xhyPWYxkjYLAX6ACITfZb2BR81OQ3FwGPWrYNWAuazZRZ/CPLrZ3geTJ7JzEoeI"
    "94lDKDVmUGxeypZAilyNqkQ9aSwa+Of5pO5Vrq4m9IS+tORtCV427Ii+rYh7xCxHmeyEZ4"
    "SEfs5263BMwoE7zbzSaCw56u6FKHbaqYUk0/XBNhkjtdkwpVojtag8UJsgUwuGEbq0385Q"
    "ViFbOjEYkqPK6QDlVuvHLjlRv/shufTWhJ3HhJzqvYjU+k2uq78WwSwBdJdMWMw57Hr5iB"
    "oieq/gSUOdzUA+HjZnPX609d7pbz7xbrWmUh1ul+T9lQwQdJ0tTyQ5omk5btiNStO11AqW"
    "njoFZ3BSnjRhk3DTVuggqUKxFbLTRv8oNKDZyoJhhFVZIvmzjB3B5gbiLPDRBmbASzgAHy"
    "LDZY2Bq8whi5eSumMrXUUAlIRLcql2iAoaLKJdZXLsE3kj6YVMM+SaXAn/cwRiWZkqJpE/"
    "bLMl5iYT+n9dLOEs6s+ZJaX82zX16wXGa2WarHYwK6DgiOhDDrgzeGgRSPAEzoiMdOTMSM"
    "D5PZIDgKmAD+pi/Ugi5i8vKYTHiSRRk66zR0Kp9FWsf5o8bj28zgSxMW7ortl8DPqox+iq"
    "xN63rF8LsIekRyhLePnopuJ59StCK2W5YLP/vcT2VPcxcOTFPhl73rj9Hw7C0EacCZhUh9"
    "yUGg4nB6TLE6wLXoePbyw+mHM0TTDwuD6Ye5WLoNLaeGO5qmUwVrtQvW+FnzOvAnyBT69c"
    "sFMXVJ/fsy5PSKH3X5wVOhdXmRp1V8qL0vmNVCa9V6pilbWOzZspvVJbqoBtOThKr+s8n1"
    "nyp1r1L3TYp9z5O6z556Wsh9EZlEfEtgX+qtEUfItYyRJskQhD2dsuQAjMeo/w/jNYnATk"
    "nU/YHtRksWKCuO2yRIWhEpS4dtuvv7MwRu2KjC0I3oy1QSsE1VAeFweAvR3dnengFdNqoQ"
    "XdGXDw4g2b0WxZfRJkhWf/nseizghV0zm7OoVpnzfv4fAxz1DQ=="
)
