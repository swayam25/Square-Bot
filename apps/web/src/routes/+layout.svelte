<script lang="ts">
    import favicon from "#lib/assets/square.svg";
    import { AUTH_CHANNEL } from "#lib/auth.ts";
    import Loader from "#lib/components/Loader.svelte";
    import PageScrollbar from "#lib/components/PageScrollbar.svelte";
    import { pageTransition } from "#lib/motion.ts";
    import { onNavigate, refreshAll } from "$app/navigation";
    import sans from "@fontsource-variable/geist/files/geist-latin-wght-normal.woff2?url";
    import mono from "@fontsource-variable/jetbrains-mono/files/jetbrains-mono-latin-wght-normal.woff2?url";
    import display from "@fontsource-variable/saira/files/saira-latin-wght-normal.woff2?url";
    import { onMount } from "svelte";
    import type { LayoutProps } from "./$types";
    import "./layout.css";

    let { children }: LayoutProps = $props();

    onNavigate(pageTransition);

    onMount(() => {
        const channel = new BroadcastChannel(AUTH_CHANNEL);
        channel.onmessage = () => refreshAll();
        return () => channel.close();
    });
</script>

<svelte:head>
    <link rel="icon" href={favicon} />
    {#each [display, sans, mono] as font (font)}
        <link rel="preload" href={font} as="font" type="font/woff2" crossorigin="anonymous" />
    {/each}
</svelte:head>

{@render children()}

<PageScrollbar />
<Loader />
