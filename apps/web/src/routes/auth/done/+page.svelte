<script lang="ts">
    import { AUTH_CHANNEL } from "#lib/auth.ts";
    import Seo from "#lib/components/site/Seo.svelte";
    import { page } from "$app/state";
    import { onMount } from "svelte";

    const guild = page.url.searchParams.get("guild");
    const invite = guild !== null || page.url.searchParams.has("invite");
    const install = page.url.searchParams.get("install");

    onMount(() => {
        const channel = new BroadcastChannel(AUTH_CHANNEL);
        channel.postMessage("changed");
        channel.close();
        window.close();
        // Only a window a script opened can close itself, so one opened by hand moves on instead
        setTimeout(() => location.replace(invite ? "/guild" : "/"), 200);
    });
</script>

<Seo
    title={guild || install === "added" ? "Square added" : invite || install ? "Square not added" : "Signed in"}
    description="This window closes on its own."
/>
