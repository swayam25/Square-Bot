<script lang="ts">
    import { openLoginPopup } from "#lib/auth.ts";
    import Button from "#lib/components/Button.svelte";
    import Chip from "#lib/components/Chip.svelte";
    import Logo from "#lib/components/Logo.svelte";
    import PlayerPreview from "#lib/components/PlayerPreview.svelte";
    import SiteFooter from "#lib/components/SiteFooter.svelte";
    import SiteHeader from "#lib/components/SiteHeader.svelte";
    import SplitBar from "#lib/components/SplitBar.svelte";
    import Toggle from "#lib/components/Toggle.svelte";
    import WavyProgress from "#lib/components/WavyProgress.svelte";
    import SimpleIconsDiscord from "~icons/simple-icons/discord";
    import SimpleIconsGithub from "~icons/simple-icons/github";
    import TablerAdjustments from "~icons/tabler/adjustments-horizontal";
    import TablerClock from "~icons/tabler/clock";
    import TablerFileText from "~icons/tabler/file-text";
    import TablerHammer from "~icons/tabler/hammer";
    import TablerLayoutDashboard from "~icons/tabler/layout-dashboard";
    import TablerLock from "~icons/tabler/lock";
    import TablerMicrophoneOff from "~icons/tabler/microphone-off";
    import TablerMusic from "~icons/tabler/music";
    import TablerShield from "~icons/tabler/shield";
    import TablerSwitchHorizontal from "~icons/tabler/switch-horizontal";
    import TablerTicket from "~icons/tabler/ticket";
    import TablerTrash from "~icons/tabler/trash";
    import TablerUserPlus from "~icons/tabler/user-plus";
    import TablerVolume3 from "~icons/tabler/volume-3";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    // The settings card's toggles work, but only on the page: they save nothing
    let autoRole = $state(true);
    let mediaOnly = $state(false);

    const tickets = [
        { id: "#0142", state: "Open", tone: "warning" },
        { id: "#0141", state: "Claimed", tone: "accent" },
        { id: "#0140", state: "Closed", tone: "success" },
    ] as const;
    const invites = [
        { label: "Regular", value: 72, class: "bg-accent" },
        { label: "Bonus", value: 14, class: "bg-emerald-400" },
        { label: "Left", value: 9, class: "bg-amber-400" },
        { label: "Fake", value: 5, class: "bg-red-400" },
    ];
</script>

<svelte:head>
    <title>Square · Advanced multipurpose Discord bot</title>
    <meta
        name="description"
        content="Advanced multipurpose Discord bot for all your needs: music with a live web player, tickets, invites, moderation and logs."
    />
</svelte:head>

<SiteHeader user={data.user} />

{#snippet heading(Icon: typeof TablerMusic, tone: string, name: string, text: string)}
    <div class="flex flex-col gap-4">
        <span class={["flex size-12 items-center justify-center rounded-2xl", tone]}><Icon class="size-6" /></span>
        <div class="flex flex-col gap-2">
            <h3 class="font-display text-xl font-semibold">{name}</h3>
            <p class="text-sm text-mist-400">{text}</p>
        </div>
    </div>
{/snippet}

<div class="overflow-x-clip">
    <section class="relative mx-auto flex max-w-6xl flex-col items-center gap-16 px-4 pt-36 pb-24 md:px-6 md:pt-44 lg:flex-row lg:gap-12">
        <!-- Soft light behind the hero, drifting slowly so the page never sits completely still -->
        <div aria-hidden="true" class="pointer-events-none absolute inset-0 -z-10">
            <div class="absolute top-24 left-0 size-96 animate-float rounded-full bg-accent/15 blur-3xl"></div>
            <div class="absolute top-48 right-0 size-80 animate-float rounded-full bg-violet-500/10 blur-3xl [animation-delay:-3s]"></div>
        </div>

        <div class="flex flex-1 flex-col items-center gap-8 text-center lg:items-start lg:text-left">
            <div class="flex animate-rise items-center gap-4 stagger" style="--i: 0">
                <Logo class="size-16" />
                <span class="font-display text-5xl font-semibold tracking-tight">Square</span>
            </div>
            <div class="flex animate-rise flex-col gap-4 stagger" style="--i: 1">
                <h1 class="max-w-xl font-display text-3xl font-semibold tracking-tight text-balance md:text-4xl">
                    Advanced multipurpose Discord bot for all your needs
                </h1>
            </div>
            <div class="flex w-full animate-rise flex-col gap-2 stagger sm:w-auto sm:flex-row" style="--i: 2">
                <Button variant="primary" size="lg" href={data.inviteUrl}><SimpleIconsDiscord />Add to Discord</Button>
                {#if data.user}
                    <Button size="lg" href="/servers"><TablerLayoutDashboard />Open dashboard</Button>
                {:else}
                    <Button size="lg" href="/login" data-sveltekit-reload onclick={(event) => openLoginPopup() && event.preventDefault()}>
                        <TablerLayoutDashboard />Open dashboard
                    </Button>
                {/if}
            </div>
            {#await data.servers then servers}
                {#if servers}
                    <p class="animate-rise text-sm text-mist-400 stagger" style="--i: 3">
                        In <span class="font-mono font-medium text-mist-100">{servers.toLocaleString("en")}</span>
                        {servers === 1 ? "server" : "servers"}
                    </p>
                {/if}
            {/await}
        </div>

        <div class="flex w-full flex-1 animate-rise justify-center stagger lg:justify-end" style="--i: 2">
            <PlayerPreview />
        </div>
    </section>

    <section aria-labelledby="features" class="bg-surface-1 py-24">
        <div class="mx-auto flex max-w-6xl flex-col gap-12 px-4 md:px-6">
            <div class="flex flex-col items-center gap-2 text-center">
                <h2 id="features" class="font-display text-3xl font-semibold tracking-tight md:text-4xl">Everything your server needs</h2>
            </div>

            <div class="grid gap-4 md:grid-cols-6">
                <article class="flex animate-rise flex-col justify-between gap-8 rounded-4xl bg-surface-2 p-6 stagger md:col-span-4" style="--i: 0">
                    {@render heading(
                        TablerMusic,
                        "bg-accent/10 text-accent",
                        "Music",
                        "YouTube, Spotify and SoundCloud with a live web player, a request channel, DJ roles, autoplay and 24/7 mode.",
                    )}
                    <WavyProgress value={0.62} />
                    <div class="flex flex-wrap gap-2">
                        {#each ["Bass Boost", "Nightcore", "Vaporwave", "8D", "Karaoke", "Soft"] as name, index (name)}
                            <Chip tone={index < 2 ? "violet" : "muted"}>{name}</Chip>
                        {/each}
                        <Chip tone="on"><TablerClock />24/7</Chip>
                    </div>
                </article>

                <article class="flex animate-rise flex-col justify-between gap-8 rounded-4xl bg-surface-2 p-6 stagger md:col-span-2" style="--i: 1">
                    {@render heading(
                        TablerTicket,
                        "bg-amber-400/10 text-amber-400",
                        "Tickets",
                        "Private tickets from a panel, with claiming and transcripts.",
                    )}
                    <ul class="flex flex-col gap-2">
                        {#each tickets as ticket (ticket.id)}
                            <li class="flex h-12 items-center justify-between rounded-2xl bg-surface-3 px-4">
                                <span class="font-mono text-sm">{ticket.id}</span>
                                <Chip tone={ticket.tone}>{ticket.state}</Chip>
                            </li>
                        {/each}
                    </ul>
                </article>

                <article class="flex animate-rise flex-col justify-between gap-8 rounded-4xl bg-surface-2 p-6 stagger md:col-span-3" style="--i: 2">
                    {@render heading(
                        TablerUserPlus,
                        "bg-emerald-400/10 text-emerald-400",
                        "Invites",
                        "See who invited whom, with leaderboards, bonus invites and fake account detection.",
                    )}
                    <div class="flex flex-col gap-4">
                        <SplitBar label="72% regular" parts={invites} />
                        <div class="flex flex-wrap gap-4 text-xs text-mist-400">
                            {#each invites as part (part.label)}
                                <span class="flex items-center gap-2"><span class={["size-2 rounded-full", part.class]}></span>{part.label}</span>
                            {/each}
                        </div>
                    </div>
                </article>

                <article class="flex animate-rise flex-col justify-between gap-8 rounded-4xl bg-surface-2 p-6 stagger md:col-span-3" style="--i: 3">
                    {@render heading(
                        TablerShield,
                        "bg-red-400/10 text-red-400",
                        "Moderation",
                        "Ban, kick, timeout and purge one member at a time or in bulk, plus voice moderation and channel locks.",
                    )}
                    <div class="flex flex-wrap gap-2">
                        <Chip tone="danger"><TablerHammer />Ban</Chip>
                        <Chip tone="warning"><TablerClock />Timeout</Chip>
                        <Chip><TablerTrash />Purge</Chip>
                        <Chip><TablerLock />Lock</Chip>
                        <Chip><TablerSwitchHorizontal />Move</Chip>
                        <Chip><TablerMicrophoneOff />Mute</Chip>
                        <Chip><TablerVolume3 />Deafen</Chip>
                    </div>
                </article>

                <article class="flex animate-rise flex-col justify-between gap-8 rounded-4xl bg-surface-2 p-6 stagger md:col-span-3" style="--i: 4">
                    {@render heading(
                        TablerFileText,
                        "bg-white/10 text-mist-100",
                        "Logs",
                        "Ten kinds of server events, each sent to the channel you pick.",
                    )}
                    <div class="flex flex-wrap gap-2">
                        {#each ["Moderation", "Members", "Messages", "Channels", "Roles", "Server", "Voice", "Invites", "AutoMod", "Tickets"] as name (name)}
                            <Chip tone="muted">{name}</Chip>
                        {/each}
                    </div>
                </article>

                <article class="flex animate-rise flex-col justify-between gap-8 rounded-4xl bg-surface-2 p-6 stagger md:col-span-3" style="--i: 5">
                    {@render heading(
                        TablerAdjustments,
                        "bg-violet-500/20 text-violet-300",
                        "Settings anywhere",
                        "Auto roles, media-only channels and the rest, from /settings in Discord or this dashboard. Both stay in sync.",
                    )}
                    <div class="flex flex-col gap-2">
                        <div class="flex h-14 items-center justify-between rounded-2xl bg-surface-3 px-4">
                            <span class="text-sm font-medium">Auto role</span>
                            <Toggle bind:checked={autoRole} label="Auto role" />
                        </div>
                        <div class="flex h-14 items-center justify-between rounded-2xl bg-surface-3 px-4">
                            <span class="text-sm font-medium">Media-only channel</span>
                            <Toggle bind:checked={mediaOnly} label="Media-only channel" />
                        </div>
                    </div>
                </article>
            </div>
        </div>
    </section>

    <section class="relative mx-auto flex max-w-6xl flex-col items-center gap-8 px-4 py-24 text-center md:px-6">
        <div aria-hidden="true" class="pointer-events-none absolute inset-x-0 top-12 -z-10 mx-auto size-72 rounded-full bg-accent/10 blur-3xl"></div>
        <Logo class="size-16" />
        <h2 class="max-w-lg font-display text-3xl font-semibold tracking-tight text-balance md:text-4xl">Bring Square to your server</h2>
        <div class="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
            <Button variant="primary" size="lg" href={data.inviteUrl}><SimpleIconsDiscord />Add to Discord</Button>
            <Button size="lg" href="https://github.com/swayam25/Square-Bot"><SimpleIconsGithub />View on GitHub</Button>
        </div>
    </section>

    <SiteFooter inviteUrl={data.inviteUrl} />
</div>
