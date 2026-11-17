<script lang="ts">
    import { AUTH_CHANNEL } from "#lib/auth.ts";
    import Seo from "#lib/components/site/Seo.svelte";
    import { onMount } from "svelte";

    onMount(() => {
        const channel = new BroadcastChannel(AUTH_CHANNEL);
        channel.postMessage("changed");
        channel.close();
        window.close();
        setTimeout(() => location.replace("/"), 200);
    });
</script>

<Seo title="Signed in" description="You're signed in to Square. This window closes on its own." />
