<script lang="ts">
    import swayamAvatar from "#lib/assets/discord/swayam.webp";
    import square from "#lib/assets/square.svg";
    import { openLoginPopup } from "#lib/auth.ts";
    import BrandIcon from "#lib/components/BrandIcon.svelte";
    import DiscordMedia from "#lib/components/discord/DiscordMedia.svelte";
    import DiscordMessage from "#lib/components/discord/DiscordMessage.svelte";
    import DiscordWindow from "#lib/components/discord/DiscordWindow.svelte";
    import InviteCard from "#lib/components/discord/InviteCard.svelte";
    import Mention from "#lib/components/discord/Mention.svelte";
    import NowPlayingCard from "#lib/components/discord/NowPlayingCard.svelte";
    import PlayerPreview from "#lib/components/PlayerPreview.svelte";
    import SiteFooter from "#lib/components/SiteFooter.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Shape from "#lib/components/ui/Shape.svelte";
    import { demo, time, TRACKS } from "#lib/demo.svelte.ts";
    import MaterialSymbolsCheckCircleRounded from "~icons/material-symbols/check-circle-rounded";
    import MaterialSymbolsConfirmationNumberRounded from "~icons/material-symbols/confirmation-number-rounded";
    import MaterialSymbolsDashboardRounded from "~icons/material-symbols/dashboard-rounded";
    import MaterialSymbolsDescriptionRounded from "~icons/material-symbols/description-rounded";
    import MaterialSymbolsMusicNoteRounded from "~icons/material-symbols/music-note-rounded";
    import MaterialSymbolsPersonAddRounded from "~icons/material-symbols/person-add-rounded";
    import MaterialSymbolsShieldRounded from "~icons/material-symbols/shield-rounded";
    import MaterialSymbolsTuneRounded from "~icons/material-symbols/tune-rounded";
    import SimpleIconsDiscord from "~icons/simple-icons/discord";
    import SimpleIconsGithub from "~icons/simple-icons/github";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    const discordContainer = "flex w-full max-w-[600px] flex-col gap-2 rounded-lg border border-[#323237] bg-[#242429] p-4";
    const discordEmoji = "mr-[0.05em] ml-[0.1em] inline size-[1.375em] align-bottom";
    const discordButton =
        "inline-flex h-8 min-w-[60px] items-center justify-center gap-2 rounded-lg px-4 py-0.5 text-sm font-medium whitespace-nowrap text-white transition-colors";

    const features = [
        {
            name: "Music",
            text: "YouTube, Spotify and SoundCloud with a live web player, filters, DJ roles and 24/7 mode.",
            icon: MaterialSymbolsMusicNoteRounded,
            lobes: 10,
            fill: "text-accent/10",
            ink: "text-accent",
        },
        {
            name: "Tickets",
            text: "Private tickets from a panel, with claiming and transcripts.",
            icon: MaterialSymbolsConfirmationNumberRounded,
            lobes: 4,
            fill: "text-amber-400/10",
            ink: "text-amber-400",
        },
        {
            name: "Invites",
            text: "See who invited whom, with leaderboards, bonus invites and fake account detection.",
            icon: MaterialSymbolsPersonAddRounded,
            lobes: 6,
            fill: "text-emerald-400/10",
            ink: "text-emerald-400",
        },
        {
            name: "Moderation",
            text: "Bans, timeouts and purges, one member at a time or in bulk, plus voice moderation and channel locks.",
            icon: MaterialSymbolsShieldRounded,
            lobes: 8,
            fill: "text-red-400/10",
            ink: "text-red-400",
        },
        {
            name: "Logs",
            text: "Ten kinds of server events, each sent to the channel you pick.",
            icon: MaterialSymbolsDescriptionRounded,
            lobes: 5,
            fill: "text-white/10",
            ink: "text-mist-100",
        },
        {
            name: "Web dashboard",
            text: dashboardText,
            icon: MaterialSymbolsTuneRounded,
            lobes: 7,
            fill: "text-violet-500/20",
            ink: "text-violet-300",
        },
    ];
</script>

{#snippet dashboardText()}
    Every setting lives on the web dashboard, and <Mention kind="command" name="settings" /> in Discord links straight to it.
{/snippet}

<svelte:head>
    <title>Square · Advanced multipurpose Discord bot</title>
    <meta
        name="description"
        content="Advanced multipurpose Discord bot for all your needs: music with a live web player, tickets, invites, moderation and logs."
    />
</svelte:head>

<div class="isolate overflow-x-clip">
    <section class="mx-auto flex max-w-6xl flex-col items-center gap-20 px-4 pt-36 pb-24 md:px-6 md:pt-44 lg:flex-row lg:gap-12">
        <div class="flex flex-1 flex-col items-center gap-8 text-center lg:items-start lg:text-left">
            <div class="flex items-center gap-4">
                <img src={square} alt="" class="size-16" />
                <span class="font-display text-5xl font-semibold tracking-tight">Square</span>
            </div>
            <h1 class="max-w-xl font-display text-3xl font-semibold tracking-tight text-balance md:text-4xl">
                Advanced multipurpose Discord bot for all your needs
            </h1>
            <div class="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
                <Button variant="primary" size="lg" href={data.inviteUrl}><SimpleIconsDiscord />Add to Discord</Button>
                {#if data.user}
                    <Button size="lg" href="/guild"><MaterialSymbolsDashboardRounded />Open dashboard</Button>
                {:else}
                    <Button size="lg" href="/login" data-sveltekit-reload onclick={(event) => openLoginPopup() && event.preventDefault()}>
                        <MaterialSymbolsDashboardRounded />Open dashboard
                    </Button>
                {/if}
            </div>
            <!-- The line keeps its height while the count streams in, so the hero doesn't jump when it lands -->
            <p class="h-5 text-sm text-mist-400">
                {#await data.servers then servers}
                    {#if servers}
                        <span class="animate-fade-in">
                            In <span class="font-mono font-medium text-mist-100">{servers.toLocaleString("en")}</span>
                            {servers === 1 ? "server" : "servers"}
                        </span>
                    {/if}
                {/await}
            </p>
        </div>

        <div class="flex w-full flex-1 justify-center lg:justify-end">
            <div class="relative w-full max-w-md">
                <div aria-hidden="true" class="pointer-events-none absolute inset-0 -z-10">
                    <Shape lobes={12} depth={0.05} class="absolute top-1/2 left-1/2 size-120 -translate-1/2 text-accent/10" />
                    <Shape lobes={4} depth={0.2} class="absolute -top-10 -left-8 size-24 rotate-12 text-violet-500/40" />
                    <Shape lobes={6} depth={0.14} class="absolute -right-6 -bottom-8 size-20 text-amber-400/30" />
                    <span class="absolute -bottom-4 -left-10 h-8 w-20 -rotate-24 rounded-full bg-emerald-400/30"></span>
                </div>
                <PlayerPreview />
            </div>
        </div>
    </section>

    <section aria-labelledby="features" class="mx-auto max-w-6xl px-4 md:px-6">
        <div class="relative isolate overflow-hidden rounded-4xl bg-surface-1 px-6 py-16 md:px-12">
            <Shape lobes={16} depth={0.04} class="absolute -bottom-32 -left-24 -z-10 size-80 text-surface-2" />
            <div class="grid gap-12 lg:grid-cols-[1fr_2fr]">
                <div class="flex flex-col gap-4">
                    <h2 id="features" class="font-display text-3xl font-semibold tracking-tight text-balance md:text-4xl">
                        Everything your server needs
                    </h2>
                    <p class="text-mist-400">One bot for music, support, growth and safety, set up from Discord or the web.</p>
                </div>
                <ul class="grid gap-x-8 gap-y-10 sm:grid-cols-2">
                    {#each features as feature (feature.name)}
                        <li class="group flex gap-4">
                            <span class="relative flex size-14 shrink-0 items-center justify-center">
                                <Shape
                                    lobes={feature.lobes}
                                    depth={feature.lobes < 6 ? 0.16 : 0.1}
                                    class={[
                                        "absolute inset-0 size-full transition-[rotate] duration-700 ease-spring group-hover:rotate-45",
                                        feature.fill,
                                    ]}
                                />
                                <feature.icon class={["relative size-6", feature.ink]} />
                            </span>
                            <div class="flex flex-col gap-2">
                                <h3 class="font-display text-lg font-semibold">{feature.name}</h3>
                                <p class="text-sm text-mist-400">
                                    {#if typeof feature.text === "string"}{feature.text}{:else}{@render feature.text()}{/if}
                                </p>
                            </div>
                        </li>
                    {/each}
                </ul>
            </div>
        </div>
    </section>

    <section aria-labelledby="in-discord" class="mx-auto flex max-w-6xl flex-col gap-24 px-4 pt-32 md:px-6">
        <div class="flex max-w-2xl flex-col gap-4">
            <h2 id="in-discord" class="font-display text-3xl font-semibold tracking-tight text-balance md:text-4xl">Right inside Discord</h2>
            <p class="text-mist-400 md:text-lg">Square answers with clean cards and buttons, so your members never have to leave the chat.</p>
        </div>

        {#snippet story(
            index: number,
            Icon: typeof MaterialSymbolsMusicNoteRounded,
            ink: string,
            eyebrow: string,
            title: string,
            text: string,
            points: string[],
        )}
            <div class={["flex flex-col gap-6", index % 2 === 1 && "lg:order-2"]}>
                <span class={["flex items-center gap-2 text-sm font-semibold", ink]}><Icon class="size-5" />{eyebrow}</span>
                <h3 class="font-display text-3xl font-semibold tracking-tight text-balance">{title}</h3>
                <p class="text-mist-400 md:text-lg">{text}</p>
                <ul class="flex flex-col gap-2">
                    {#each points as point (point)}
                        <li class="flex items-center gap-2 text-sm"><MaterialSymbolsCheckCircleRounded class={["size-5 shrink-0", ink]} />{point}</li>
                    {/each}
                </ul>
            </div>
        {/snippet}

        <article class="grid items-center gap-12 lg:grid-cols-2">
            {@render story(
                0,
                MaterialSymbolsMusicNoteRounded,
                "text-accent",
                "Music",
                "A player that lives in the chat",
                "Every song gets a live card with its own buttons, and the same player runs on the web.",
                ["YouTube, Spotify and SoundCloud", "Filters, EQ and autoplay", "Request channel and 24/7 mode"],
            )}
            <div class="relative isolate">
                <Shape lobes={12} depth={0.05} class="absolute -top-16 -right-16 -z-10 size-72 text-accent/10" />
                <span aria-hidden="true" class="absolute -bottom-4 -left-6 -z-10 h-8 w-20 -rotate-24 rounded-full bg-violet-500/30"></span>
                <DiscordWindow channel="music">
                    <DiscordMessage command="play">
                        <div class={[discordContainer, "border-l-4 border-l-[#e74c3c]"]}>
                            <p>
                                <BrandIcon brand="youtube" class={discordEmoji} /> Added
                                <span class="text-[#4d96ee]"><strong>{demo.track.title}</strong> by <strong>{demo.track.author}</strong></span>
                                [{time(demo.track.duration)}].
                            </p>
                        </div>
                    </DiscordMessage>
                    <DiscordMessage command="now-playing" ephemeral>
                        <div class={discordContainer}>
                            <DiscordMedia>
                                <NowPlayingCard
                                    data={{
                                        title: demo.track.title,
                                        author: demo.track.author,
                                        source: "youtube",
                                        artwork: demo.track.artwork,
                                        requester: "Swayam",
                                        requesterAvatar: swayamAvatar,
                                        progress: demo.elapsed / demo.track.duration,
                                        elapsed: time(demo.elapsed),
                                        duration: time(demo.track.duration),
                                        stream: false,
                                        paused: !demo.playing,
                                        volume: 80,
                                        loop: "Disabled",
                                        shuffle: false,
                                        autoplay: true,
                                        filters: demo.filters,
                                        upNext: `${demo.next.title} by ${demo.next.author}`,
                                        upNextArtwork: demo.next.artwork,
                                        queued: TRACKS.length - 1,
                                    }}
                                />
                            </DiscordMedia>
                        </div>
                        <div class="flex flex-wrap gap-2">
                            <span class={[discordButton, "border border-[#97979f]/4 bg-[#97979f]/12"]}>
                                <BrandIcon brand="youtube" class="size-4.5" />Open on YouTube
                                <svg
                                    viewBox="0 0 24 24"
                                    aria-hidden="true"
                                    class="size-4 fill-none stroke-current stroke-2 [stroke-linecap:round] [stroke-linejoin:round]"
                                >
                                    <path d="M14 4h6v6m0-6-9 9m7 1v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4" />
                                </svg>
                            </span>
                        </div>
                    </DiscordMessage>
                </DiscordWindow>
            </div>
        </article>

        <article class="grid items-center gap-12 lg:grid-cols-2">
            {@render story(
                1,
                MaterialSymbolsPersonAddRounded,
                "text-emerald-400",
                "Invites",
                "Know who grows your server",
                "Ask for anyone's invites and get the full picture in one card.",
                ["Regular, bonus, left and fake invites", "Server leaderboards", "Fake accounts caught by account age"],
            )}
            <div class="relative isolate">
                <Shape lobes={6} depth={0.14} class="absolute -top-12 -left-12 -z-10 size-56 text-emerald-400/10" />
                <Shape lobes={4} depth={0.2} class="absolute -right-6 -bottom-8 -z-10 size-20 rotate-12 text-amber-400/30" />
                <DiscordWindow channel="general">
                    <DiscordMessage command="invites">
                        <div class={discordContainer}>
                            <DiscordMedia>
                                <InviteCard
                                    data={{
                                        name: "Swayam",
                                        username: "_swayam25",
                                        avatar: swayamAvatar,
                                        guildName: "Square HQ",
                                        guildIcon: square,
                                        rank: 2,
                                        regular: 142,
                                        left: 9,
                                        fake: 5,
                                        bonus: 14,
                                        fakeDays: 7,
                                    }}
                                />
                            </DiscordMedia>
                        </div>
                    </DiscordMessage>
                </DiscordWindow>
            </div>
        </article>

        <article class="grid items-center gap-12 lg:grid-cols-2">
            {@render story(
                2,
                MaterialSymbolsConfirmationNumberRounded,
                "text-amber-400",
                "Tickets",
                "Support without the mess",
                "Members open a private ticket from one panel. Staff claim it, and Square keeps a transcript when it closes.",
                ["One button to open a ticket", "Claiming for staff", "Transcripts of every ticket"],
            )}
            <div class="relative isolate">
                <Shape lobes={4} depth={0.2} class="absolute -top-12 -right-10 -z-10 size-48 rotate-12 text-amber-400/10" />
                <span aria-hidden="true" class="absolute -bottom-4 -left-8 -z-10 h-8 w-20 rotate-12 rounded-full bg-accent/20"></span>
                <DiscordWindow channel="support">
                    <DiscordMessage>
                        <div class={discordContainer}>
                            <h2 class="mb-2 text-xl leading-snug font-bold text-[#fbfbfb]">Need Help?</h2>
                            <p>Press the button below to open a ticket. Staff will reply in a private channel.</p>
                        </div>
                        <div class="flex flex-wrap gap-2">
                            <button type="button" class={[discordButton, "bg-[#5865f2] hover:bg-[#4752c4]"]}>
                                <MaterialSymbolsConfirmationNumberRounded class="size-4.5" />Open a ticket
                            </button>
                        </div>
                    </DiscordMessage>
                </DiscordWindow>
            </div>
        </article>
    </section>

    <section
        aria-labelledby="join"
        class="relative isolate mx-auto flex max-w-4xl flex-col items-center gap-8 px-4 py-32 text-center md:px-6 md:py-40"
    >
        <div aria-hidden="true" class="pointer-events-none absolute inset-0 -z-10">
            <Shape lobes={12} depth={0.05} class="absolute top-16 -left-8 size-32 text-accent/20 md:left-0 md:size-40" />
            <Shape lobes={4} depth={0.2} class="absolute top-12 right-0 size-20 rotate-12 text-violet-500/30 md:right-8" />
            <Shape lobes={6} depth={0.14} class="absolute right-4 bottom-16 size-24 text-amber-400/20 md:right-16" />
            <span class="absolute bottom-20 left-8 h-8 w-20 -rotate-24 rounded-full bg-emerald-400/20 md:left-24"></span>
        </div>
        <h2 id="join" class="max-w-2xl font-display text-4xl font-semibold tracking-tight text-balance md:text-6xl">Ready to bring Square in?</h2>
        <p class="max-w-md text-mist-400 md:text-lg">Add it in a few clicks, then set it up from Discord or the dashboard.</p>
        <div class="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
            <Button variant="primary" size="lg" href={data.inviteUrl}><SimpleIconsDiscord />Add to Discord</Button>
            <Button size="lg" href="https://github.com/swayam25/Square-Bot"><SimpleIconsGithub />View on GitHub</Button>
        </div>
    </section>

    <SiteFooter inviteUrl={data.inviteUrl} />
</div>
