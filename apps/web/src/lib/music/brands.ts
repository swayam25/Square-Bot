import type { Component } from "svelte";
import ThesvgColorAppleMusic from "~icons/thesvg-color/apple-music";
import ThesvgColorBandcamp from "~icons/thesvg-color/bandcamp";
import ThesvgColorDeezer from "~icons/thesvg-color/deezer";
import ThesvgColorSoundcloudDark from "~icons/thesvg-color/soundcloud-dark";
import ThesvgColorSpotify from "~icons/thesvg-color/spotify";
import ThesvgColorTwitch from "~icons/thesvg-color/twitch";
import ThesvgColorVimeo from "~icons/thesvg-color/vimeo";
import ThesvgColorYoutube from "~icons/thesvg-color/youtube";
import ThesvgColorYoutubeMusic from "~icons/thesvg-color/youtube-music";

export type Brand = "youtube_music" | "youtube" | "spotify" | "apple_music" | "soundcloud" | "deezer" | "bandcamp" | "twitch" | "vimeo";

export const LOGOS: Record<Brand, Component> = {
    youtube_music: ThesvgColorYoutubeMusic,
    youtube: ThesvgColorYoutube,
    spotify: ThesvgColorSpotify,
    apple_music: ThesvgColorAppleMusic,
    soundcloud: ThesvgColorSoundcloudDark,
    deezer: ThesvgColorDeezer,
    bandcamp: ThesvgColorBandcamp,
    twitch: ThesvgColorTwitch,
    vimeo: ThesvgColorVimeo,
};

const SOURCES: Record<string, Brand> = {
    youtube: "youtube",
    spotify: "spotify",
    applemusic: "apple_music",
    soundcloud: "soundcloud",
    deezer: "deezer",
    bandcamp: "bandcamp",
    twitch: "twitch",
    vimeo: "vimeo",
};

export const brandOf = (source: string): Brand | undefined => SOURCES[source];
