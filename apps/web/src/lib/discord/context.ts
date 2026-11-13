import type { TranscriptFile, TranscriptRole, TranscriptUser } from "@square/api-client";
import { getContext, setContext } from "svelte";

export type DiscordContext = {
    users: Record<string, TranscriptUser>;
    roles: Record<string, TranscriptRole>;
    channels: Record<string, string>;
    fileUrl: (file: TranscriptFile) => string | null;
    // Opens a picture large. Left out where there's no viewer, and pictures then don't react to clicks
    view?: (src: string) => void;
};

const KEY = Symbol("discord");
const PLAIN: DiscordContext = { users: {}, roles: {}, channels: {}, fileUrl: (file) => file.url };

// Pass getters, so the components keep up when the data changes
export const setDiscord = (context: DiscordContext) => setContext(KEY, context);
// Mockups have no names to look up, so the components work without a context too
export const getDiscord = () => getContext<DiscordContext | undefined>(KEY) ?? PLAIN;
