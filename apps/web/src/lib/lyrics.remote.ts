import { actor } from "#lib/server/bot.ts";
import { findLyrics } from "#lib/server/lyrics.ts";
import { query } from "$app/server";
import { z } from "zod";

// Signed-in only, so the dashboard can't be used as an open proxy for the lyric services
export const trackLyrics = query(
    z.object({ title: z.string().min(1).max(300), artist: z.string().max(300), durationMs: z.number().int().min(0).max(86_400_000) }),
    (track) => findLyrics(track, actor()),
);
