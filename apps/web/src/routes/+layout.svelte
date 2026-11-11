<script lang="ts">
    import favicon from "#lib/assets/square.svg";
    import { AUTH_CHANNEL } from "#lib/auth.ts";
    import Loader from "#lib/components/Loader.svelte";
    import { pageTransition } from "#lib/motion.ts";
    import { onNavigate, refreshAll } from "$app/navigation";
    import mono from "@fontsource-variable/jetbrains-mono/files/jetbrains-mono-latin-wght-normal.woff2?url";
    import sans from "@fontsource-variable/geist/files/geist-latin-wght-normal.woff2?url";
    import display from "@fontsource-variable/saira/files/saira-latin-wght-normal.woff2?url";
    import { onMount } from "svelte";
    import type { LayoutProps } from "./$types";
    import "./layout.css";

    let { children }: LayoutProps = $props();

    onNavigate(pageTransition);

    // A login popup (or another tab) changed the session cookie, so reload data to pick it up
    onMount(() => {
        const channel = new BroadcastChannel(AUTH_CHANNEL);
        channel.onmessage = () => refreshAll();
        return () => channel.close();
    });
</script>

<svelte:head>
    <link rel="icon" href={favicon} />
    <!-- The Latin files every page uses, fetched with the HTML instead of after the CSS, so text doesn't flash in a fallback font -->
    {#each [display, sans, mono] as font (font)}
        <link rel="preload" href={font} as="font" type="font/woff2" crossorigin="anonymous" />
    {/each}
</svelte:head>

{@render children()}

<Loader />
