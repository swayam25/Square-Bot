<script lang="ts">
    import type { PageProps } from "./$types";
    import Composer from "./Composer.svelte";

    let { data }: PageProps = $props();
</script>

<!-- Each server keeps its own draft, so switching servers starts the editor over -->
{#key data.guild.id}
    <Composer guild={data.guild} user={data.user ?? null} />
{/key}
