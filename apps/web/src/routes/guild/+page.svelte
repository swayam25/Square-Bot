<script lang="ts">
    import { openPopup } from "#lib/auth.ts";
    import SiteHeader from "#lib/components/SiteHeader.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import GuildIcon from "#lib/components/ui/GuildIcon.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Shape from "#lib/components/ui/Shape.svelte";
    import { ripple } from "#lib/motion.ts";
    import { refreshAll } from "$app/navigation";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import MaterialSymbolsArrowForwardRounded from "~icons/material-symbols/arrow-forward-rounded";
    import MaterialSymbolsMusicNoteRounded from "~icons/material-symbols/music-note-rounded";
    import MaterialSymbolsSearchRounded from "~icons/material-symbols/search-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    let search = $state("");
    const query = $derived(search.trim().toLowerCase());
    const matches = (guild: { name: string }) => guild.name.toLowerCase().includes(query);
    const guilds = $derived(data.guilds.filter(matches));
    const invitable = $derived(data.invitable.filter(matches));
    const searchable = $derived(data.guilds.length + data.invitable.length > 8);

    function invite(event: MouseEvent & { currentTarget: HTMLAnchorElement }) {
        addEventListener("focus", () => refreshAll(), { once: true });
        if (event.ctrlKey || event.metaKey || event.shiftKey) return;
        if (openPopup(event.currentTarget.href, "square-invite")) event.preventDefault();
    }

    const focusRing = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";
</script>

<svelte:head>
    <title>Your servers · Square</title>
</svelte:head>

<SiteHeader user={data.user} />

<main class="mx-auto flex max-w-6xl flex-col gap-20 px-4 pt-32 pb-24 md:px-6 md:pt-40">
    <section aria-labelledby="servers" class="flex animate-rise flex-col gap-8">
        <div class="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div class="flex flex-col gap-2">
                <h1 id="servers" class="font-display text-3xl font-semibold tracking-tight md:text-4xl">Your servers</h1>
                <p class="text-mist-400">Pick a server to open its dashboard.</p>
            </div>
            <div class="flex gap-2">
                {#if searchable}
                    <Input
                        type="search"
                        icon={MaterialSymbolsSearchRounded}
                        placeholder="Search"
                        aria-label="Search servers"
                        bind:value={search}
                        class="flex-1 md:w-64 md:flex-none"
                    />
                {/if}
                <Button href={data.inviteUrl} target="_blank" rel="noopener" onclick={invite}>
                    <MaterialSymbolsAddRounded />Add to server
                </Button>
            </div>
        </div>

        {#if guilds.length}
            <ul class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {#each guilds as guild (guild.id)}
                    <li>
                        <a
                            href="/guild/{guild.id}"
                            class={["group ripple flex flex-col rounded-4xl bg-surface-1 p-2 hover:bg-surface-2", focusRing]}
                            {@attach ripple}
                        >
                            <div class="relative isolate flex h-32 items-center justify-center overflow-hidden rounded-3xl bg-surface-2">
                                {#if guild.iconUrl}
                                    <img
                                        src={guild.iconUrl}
                                        alt=""
                                        class="absolute inset-0 -z-10 size-full scale-150 object-cover opacity-60 blur-2xl"
                                    />
                                {:else}
                                    <Shape lobes={12} depth={0.05} class="absolute -z-10 size-48 text-surface-3" />
                                {/if}
                                <GuildIcon src={guild.iconUrl} name={guild.name} class="size-16 rounded-2xl shadow-lg shadow-black/20" />
                                {#if !guild.canManage}
                                    <Chip tone="muted" class="absolute top-2 right-2 backdrop-blur-xl">
                                        <MaterialSymbolsMusicNoteRounded />Music only
                                    </Chip>
                                {/if}
                            </div>
                            <div class="flex items-center gap-4 p-4 pb-2">
                                <div class="flex min-w-0 flex-1 flex-col">
                                    <h2 class="truncate font-display text-lg font-semibold">{guild.name}</h2>
                                    <p class="font-mono text-xs text-mist-400">
                                        {guild.memberCount.toLocaleString("en-US")}
                                        {guild.memberCount === 1 ? "member" : "members"}
                                    </p>
                                </div>
                                <MaterialSymbolsArrowForwardRounded
                                    class="size-6 shrink-0 text-mist-400 transition-transform duration-200 group-hover:translate-x-1 group-hover:text-mist-100"
                                />
                            </div>
                        </a>
                    </li>
                {/each}
            </ul>
        {:else if query}
            <p class="text-mist-400">No servers match "{search.trim()}".</p>
        {:else}
            <div class="relative isolate flex flex-col items-center gap-6 py-16 text-center">
                <Shape lobes={12} depth={0.05} class="absolute top-1/2 left-1/2 -z-10 size-72 -translate-1/2 animate-spin-in text-accent/10" />
                <div class="flex flex-col gap-2">
                    <h2 class="font-display text-2xl font-semibold tracking-tight">Square isn't in any of your servers yet</h2>
                    <p class="max-w-md text-mist-400">Add it to a server you manage, or ask a server owner to add it.</p>
                </div>
                <Button variant="primary" size="lg" href={data.inviteUrl} target="_blank" rel="noopener" onclick={invite}>
                    <MaterialSymbolsAddRounded />Add Square
                </Button>
            </div>
        {/if}
    </section>

    {#if invitable.length}
        <section aria-labelledby="add" class="flex animate-rise flex-col gap-8">
            <div class="flex flex-col gap-2">
                <h2 id="add" class="font-display text-2xl font-semibold tracking-tight">Add Square</h2>
                <p class="text-mist-400">Servers you manage that don't have Square yet.</p>
            </div>
            <ul class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {#each invitable as guild (guild.id)}
                    <li>
                        <a
                            href={guild.inviteUrl}
                            target="_blank"
                            rel="noopener"
                            onclick={invite}
                            class={["group ripple flex items-center gap-4 rounded-3xl bg-surface-1 p-2 pr-4 hover:bg-surface-2", focusRing]}
                            {@attach ripple}
                        >
                            <GuildIcon src={guild.iconUrl} name={guild.name} class="size-12 rounded-xl" />
                            <span class="min-w-0 flex-1 truncate font-medium">{guild.name}</span>
                            <span class="flex items-center gap-1 text-sm font-medium text-mist-400 group-hover:text-accent">
                                <MaterialSymbolsAddRounded class="size-5" />Add
                            </span>
                        </a>
                    </li>
                {/each}
            </ul>
        </section>
    {/if}
</main>
