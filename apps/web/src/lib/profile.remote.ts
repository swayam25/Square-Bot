import { BIO_MAX, IMAGE_MAX_BYTES, NICK_MAX } from "#lib/profile.ts";
import { forGuild, read } from "#lib/server/bot.ts";
import { command, query } from "$app/server";
import * as sdk from "@square/api-client";
import { z } from "zod";

const snowflake = z.string().regex(/^\d{17,20}$/);
const image = z
    .string()
    .regex(/^data:image\/(png|jpeg|gif);base64,/)
    .max(Math.ceil(IMAGE_MAX_BYTES / 3) * 4 + 32);

export const botProfile = query(snowflake, (guild) => read(sdk.getBotProfile(forGuild(guild))));

export const updateBotProfile = command(
    z.object({
        guild: snowflake,
        nick: z.string().trim().min(1).max(NICK_MAX).nullable().optional(),
        bio: z.string().trim().min(1).max(BIO_MAX).nullable().optional(),
        avatar: image.nullable().optional(),
        banner: image.nullable().optional(),
    }),
    async ({ guild, ...body }) => {
        botProfile(guild).set(await read(sdk.updateBotProfile({ ...forGuild(guild), body })));
    },
);

export const resetBotProfile = command(snowflake, (guild) => read(sdk.resetBotProfile(forGuild(guild))));
