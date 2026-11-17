<script lang="ts">
    import { AUTH_CHANNEL } from "#lib/auth.ts";
    import Island from "#lib/components/site/Island.svelte";
    import Loader from "#lib/components/site/Loader.svelte";
    import PageScrollbar from "#lib/components/site/PageScrollbar.svelte";
    import SiteHeader from "#lib/components/site/SiteHeader.svelte";
    import { refreshAll } from "$app/navigation";
    import { page } from "$app/state";
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

{#if !dashboard}<SiteHeader />{/if}

<!-- Dashboard pages fade only their content, in the `{#key page.url.pathname}` block inside `<main>` of `guild/[guildId]/+layout.svelte`, so the sidebar never re-renders. Fading here too doubles it -->
{#key dashboard ? "dashboard" : page.url.pathname}
    <div class={[!dashboard && "animate-page-in"]}>{@render children()}</div>
{/key}

{#if !dashboard}<Island />{/if}
<PageScrollbar />
<Loader />
