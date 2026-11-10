<script lang="ts">
    import { AUTH_CHANNEL } from "#lib/auth.ts";
    import { onMount } from "svelte";

    onMount(() => {
        const channel = new BroadcastChannel(AUTH_CHANNEL);
        channel.postMessage("changed");
        channel.close();
        window.close();
        // Still open: the browser didn't treat this as a script-opened popup, so carry on in this tab
        setTimeout(() => location.replace("/"), 200);
    });
</script>
