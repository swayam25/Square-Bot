<script lang="ts">
    import Button from "#lib/components/Button.svelte";
    import SiteHeader from "#lib/components/SiteHeader.svelte";
    import { page } from "$app/state";
    import MaterialSymbolsHomeRounded from "~icons/material-symbols/home-rounded";
    import MaterialSymbolsRefreshRounded from "~icons/material-symbols/refresh-rounded";

    const titles: Record<number, [string, string]> = {
        400: ["That didn't work", "Something about that request was off. Go back and try again."],
        401: ["Log in first", "This page needs you to be logged in with Discord."],
        403: ["Not for you", "You don't have access to this. Ask a server manager if you think you should."],
        404: ["Page not found", "This page doesn't exist, or it moved."],
        503: ["Square is offline", "The bot isn't answering right now. It's usually back in a minute."],
    };

    const status = $derived(page.status);
    const [title, fallback] = $derived(titles[status] ?? ["Something went wrong", "An unexpected error got in the way. Try again in a moment."]);
    const detail = $derived(page.error?.message && page.error.message !== "Not Found" && status !== 500 ? page.error.message : fallback);
    const retryable = $derived(status >= 500 || status === 429);
</script>

<svelte:head>
    <title>{title} · Square</title>
</svelte:head>

<SiteHeader user={page.data.user} />

<main class="mx-auto flex min-h-dvh max-w-xl flex-col items-center justify-center gap-8 px-4 pt-28 pb-16 text-center">
    <span class="animate-rise font-mono text-5xl font-medium tracking-tight text-accent stagger" style="--i: 0">{status}</span>
    <div class="flex animate-rise flex-col gap-2 stagger" style="--i: 1">
        <h1 class="font-display text-3xl font-semibold tracking-tight">{title}</h1>
        <p class="text-base text-mist-400">{detail}</p>
    </div>
    <div class="flex w-full animate-rise flex-col gap-2 stagger sm:w-auto sm:flex-row" style="--i: 2">
        {#if retryable}
            <Button variant="primary" onclick={() => location.reload()}><MaterialSymbolsRefreshRounded />Try again</Button>
            <Button href="/"><MaterialSymbolsHomeRounded />Go home</Button>
        {:else}
            <Button variant="primary" href="/"><MaterialSymbolsHomeRounded />Go home</Button>
        {/if}
    </div>
</main>
