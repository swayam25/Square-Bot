<script module lang="ts">
    import type { Component } from "svelte";
    import SimpleIconsApplemusic from "~icons/simple-icons/applemusic";
    import SimpleIconsSoundcloud from "~icons/simple-icons/soundcloud";
    import SimpleIconsSpotify from "~icons/simple-icons/spotify";
    import SimpleIconsYoutube from "~icons/simple-icons/youtube";
    import SimpleIconsYoutubemusic from "~icons/simple-icons/youtubemusic";

    export type Brand = "youtube_music" | "youtube" | "spotify" | "apple_music" | "soundcloud";

    // The logos are one-colour shapes whose marks are holes; the backing fills those holes white like the real ones.
    // Spotify's bars are black in its own logo, so it gets no backing.
    const BRANDS: Record<Brand, { icon: Component; color: string; backing?: string }> = {
        youtube_music: { icon: SimpleIconsYoutubemusic, color: "#ff0000", backing: "inset-[18%] rounded-full" },
        youtube: { icon: SimpleIconsYoutube, color: "#ff0000", backing: "inset-x-[30%] inset-y-[32%]" },
        spotify: { icon: SimpleIconsSpotify, color: "#1ed760" },
        apple_music: { icon: SimpleIconsApplemusic, color: "#fa243c", backing: "inset-[20%]" },
        soundcloud: { icon: SimpleIconsSoundcloud, color: "#ff5500" },
    };

    const SOURCES: Record<string, Brand> = { youtube: "youtube", spotify: "spotify", applemusic: "apple_music", soundcloud: "soundcloud" };
    export const brandOf = (source: string): Brand | undefined => SOURCES[source];
</script>

<script lang="ts">
    import type { ClassValue } from "svelte/elements";

    let { brand, class: className }: { brand: Brand; class?: ClassValue } = $props();

    const { icon: Icon, color, backing } = $derived(BRANDS[brand]);
</script>

<span aria-hidden="true" class={["relative inline-flex shrink-0", className]}>
    {#if backing}<span class={["absolute bg-white", backing]}></span>{/if}
    <Icon class="relative size-full" style="color: {color}" />
</span>
