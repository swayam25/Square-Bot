import type { TranscriptFile, TranscriptRole, TranscriptUser } from "@square/api-client";
import { getContext, setContext } from "svelte";

export type ViewerMedia = { src: string; kind: "image" | "video" | "gif"; name?: string; width?: number | null; height?: number | null };
export type ViewerAuthor = { name: string; avatar?: string | null; time: string };
export type Viewing = { media: ViewerMedia[]; index: number; author?: ViewerAuthor };

export type ChannelName = { name: string; voice?: boolean; guild?: { name: string; iconUrl: string | null } };

export type DiscordContext = {
    user: (id: string) => Pick<TranscriptUser, "name"> | null | undefined;
    role: (id: string) => TranscriptRole | null | undefined;
    channel: (id: string) => ChannelName | null | undefined;
    fileUrl: (file: TranscriptFile) => string | null;
    // Opens a message's media large. Left out where there's no viewer, and media then doesn't react to clicks
    view?: (viewing: Viewing) => void;
};

const KEY = Symbol("discord");
const MESSAGE = Symbol("discord-message");
const PLAIN: DiscordContext = { user: () => null, role: () => null, channel: () => null, fileUrl: (file) => file.url };

// Pass getters, so the components keep up when the data changes
export const setDiscord = (context: DiscordContext) => setContext(KEY, context);
export const getDiscord = () => getContext<DiscordContext | undefined>(KEY) ?? PLAIN;

export const setMessageAuthor = (author: ViewerAuthor) => setContext(MESSAGE, author);
export const getMessageAuthor = () => getContext<ViewerAuthor | undefined>(MESSAGE);
