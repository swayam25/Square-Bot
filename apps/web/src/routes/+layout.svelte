<script lang="ts">
    import favicon from "#lib/assets/favicon.svg";
    import { AUTH_CHANNEL } from "#lib/auth.ts";
    import { refreshAll } from "$app/navigation";
    import { onMount } from "svelte";
    import type { LayoutProps } from "./$types";
    import "./layout.css";

    let { children }: LayoutProps = $props();

    // A login popup (or another tab) changed the session cookie, so reload data to pick it up
    onMount(() => {
        const channel = new BroadcastChannel(AUTH_CHANNEL);
        channel.onmessage = () => refreshAll();
        return () => channel.close();
    });
</script>

<svelte:head>
    <link rel="icon" href={favicon} />
</svelte:head>

{@render children()}
