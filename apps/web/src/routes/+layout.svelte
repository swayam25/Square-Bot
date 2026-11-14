<script lang="ts">
    import favicon from "#lib/assets/square.svg";
    import { AUTH_CHANNEL } from "#lib/auth.ts";
    import Island from "#lib/components/Island.svelte";
    import Loader from "#lib/components/Loader.svelte";
    import PageScrollbar from "#lib/components/PageScrollbar.svelte";
    import SiteHeader from "#lib/components/SiteHeader.svelte";
    import { refreshAll } from "$app/navigation";
    import { page } from "$app/state";
    import mono from "@fontsource-variable/jetbrains-mono/files/jetbrains-mono-latin-wght-normal.woff2?url";
    import sans from "@fontsource-variable/noto-sans/files/noto-sans-latin-wght-normal.woff2?url";
    import display from "@fontsource-variable/saira/files/saira-latin-wght-normal.woff2?url";
    import { onMount } from "svelte";
    import type { LayoutProps } from "./$types";
    import "./layout.css";

    let { children }: LayoutProps = $props();

    const dashboard = $derived(!page.error && !!page.route.id?.startsWith("/guild/[guildId]"));

    onMount(() => {
        const channel = new BroadcastChannel(AUTH_CHANNEL);
        channel.onmessage = () => refreshAll();
        return () => channel.close();
    });
</script>

<svelte:head>
    <link rel="icon" href={favicon} type="image/svg+xml" />
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
    {#each [display, sans, mono] as font (font)}
        <link rel="preload" href={font} as="font" type="font/woff2" crossorigin="anonymous" />
    {/each}
</svelte:head>

{#if !dashboard}<SiteHeader />{/if}

<!-- Dashboard pages fade only their content, in the `{#key page.url.pathname}` block inside `<main>` of `guild/[guildId]/+layout.svelte`, so the sidebar never re-renders. Fading here too doubles it -->
{#key dashboard ? "dashboard" : page.url.pathname}
    <div class={[!dashboard && "animate-page-in"]}>{@render children()}</div>
{/key}

{#if !dashboard}<Island />{/if}
<PageScrollbar />
<Loader />
