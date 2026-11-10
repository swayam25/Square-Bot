<script lang="ts">
    import { openLoginPopup } from "#lib/auth.ts";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();
</script>

{#if data.user}
    <p>Logged in as {data.user.globalName ?? data.user.username}</p>
    <form method="POST" action="/logout"><button>Log out</button></form>

    <h2>Your servers</h2>
    <ul>
        {#each data.guilds as guild (guild.id)}
            <li>{guild.name} · {guild.memberCount} members</li>
        {:else}
            <li>None yet</li>
        {/each}
    </ul>

    <h2>Add Square</h2>
    <ul>
        {#each data.invitable as guild (guild.id)}
            <li><a href={guild.inviteUrl}>{guild.name}</a></li>
        {/each}
    </ul>
{:else}
    <a href="/login" data-sveltekit-reload onclick={(event) => openLoginPopup() && event.preventDefault()}>Log in with Discord</a>
{/if}
