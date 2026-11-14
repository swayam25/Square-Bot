<script lang="ts">
    import DiscordTooltip from "#lib/components/discord/DiscordTooltip.svelte";
    import DiscordTranscript from "#lib/components/discord/DiscordTranscript.svelte";
    import PageHeading from "#lib/components/PageHeading.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import Fact from "#lib/components/ui/Fact.svelte";
    import PersonRow from "#lib/components/ui/PersonRow.svelte";
    import { fullTime } from "#lib/discord/markdown.ts";
    import { dateTime, plural } from "#lib/format.ts";
    import * as tickets from "#lib/tickets.remote.ts";
    import { statusName, statusTone } from "#lib/tickets.ts";
    import { page } from "$app/state";
    import type { TranscriptFile } from "@square/api-client";
    import MaterialSymbolsArrowBackRounded from "~icons/material-symbols/arrow-back-rounded";
    import MaterialSymbolsConfirmationNumberRounded from "~icons/material-symbols/confirmation-number-rounded";
    import MaterialSymbolsDescriptionRounded from "~icons/material-symbols/description-rounded";
    import MaterialSymbolsOpenInNewRounded from "~icons/material-symbols/open-in-new-rounded";
    import MaterialSymbolsRefreshRounded from "~icons/material-symbols/refresh-rounded";
    import type { PageProps } from "./$types";
    import TranscriptSkeleton from "./TranscriptSkeleton.svelte";

    let { data }: PageProps = $props();

    const guild = $derived(data.guild.id);
    const number = $derived(Number(page.params.number));
    const valid = $derived(Number.isInteger(number) && number >= 1 && number <= 10_000_000);
    const query = $derived(valid ? tickets.ticketTranscript({ guild, number }) : null);
    const loaded = $derived(query?.current);
    const ticket = $derived(loaded?.ticket);
    const transcript = $derived(loaded?.transcript);
    const title = $derived(`Ticket #${valid ? String(number).padStart(4, "0") : "?"}`);

    function lasted(from: number, to: number) {
        const minutes = Math.max(1, Math.round((to - from) / 60_000));
        if (minutes < 60) return plural(minutes, "minute");
        if (minutes < 60 * 24) return plural(Math.round(minutes / 60), "hour");
        return plural(Math.round(minutes / (60 * 24)), "day");
    }

    // Discord's own links to a channel's files stop working about a day after they're made, and for good once it's deleted
    const EXPIRING = /^https:\/\/(cdn\.discordapp\.com|media\.discordapp\.net)\/(ephemeral-)?attachments\//;
    function fileUrl(file: TranscriptFile) {
        if (file.stored && file.id) return `/guild/${guild}/tickets/${number}/files/${file.id}`;
        return loaded?.live || !EXPIRING.test(file.url) ? file.url : null;
    }

    let refreshing = $state(false);
    async function refresh() {
        refreshing = true;
        try {
            await query?.refresh();
        } finally {
            refreshing = false;
        }
    }
</script>

{#snippet people()}
    {#if ticket && transcript}
        <div class="flex flex-col gap-3">
            <div class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-medium text-dc-muted">In this ticket</span>
                {#each ticket.people as who (who.id)}
                    <span
                        class="flex h-7 max-w-full items-center gap-2 rounded-full border border-dc-border bg-dc-surface pr-3 pl-0.5 text-sm font-medium"
                    >
                        <Avatar src={who.avatarUrl} name={who.name} class="size-5.5 text-2xs" />
                        <span class="truncate">{who.name}</span>
                    </span>
                {/each}
            </div>
            <p class="text-xs font-medium text-dc-muted">
                {plural(transcript.messages.length, "message")} • Saved
                <DiscordTooltip content={fullTime(transcript.savedAt)}><time>{dateTime.format(transcript.savedAt)}</time></DiscordTooltip>
            </p>
        </div>
    {/if}
{/snippet}

<div class="flex flex-col gap-6">
    <PageHeading {title} description={ticket ? ticket.reason : undefined}>
        {#snippet actions()}
            {#if data.guild.canManage}
                <Button href="/guild/{guild}/tickets"><MaterialSymbolsArrowBackRounded />All tickets</Button>
            {/if}
            {#if ticket?.channelId}
                <Button variant="ghost" href="https://discord.com/channels/{guild}/{ticket.channelId}" target="_blank" rel="noopener">
                    <MaterialSymbolsOpenInNewRounded />Open in Discord
                </Button>
            {/if}
        {/snippet}
    </PageHeading>

    {#if !valid}
        <EmptyState card icon={MaterialSymbolsConfirmationNumberRounded} title="No such ticket" text="That isn't a ticket number." />
    {:else if query?.error}
        <EmptyState
            tone="danger"
            card
            title="Couldn't load this ticket"
            text={query.error.message ?? "Square didn't answer. Try again in a moment."}
            retry={() => query.refresh()}
        />
    {:else if !ticket}
        <TranscriptSkeleton />
    {:else}
        <div class="grid grid-cols-2 gap-2 rounded-3xl bg-gray-900 p-2 md:grid-cols-3">
            <PersonRow label="Opened by" person={ticket.opener} />
            <PersonRow label="Claimed by" person={ticket.claimedBy} />
            {#if ticket.status !== "open"}<PersonRow label="Closed by" person={ticket.closedBy} />{/if}
            <Fact label="Opened" value={dateTime.format(ticket.createdAt)} />
            {#if ticket.closedAt}
                <Fact label="Closed" value={dateTime.format(ticket.closedAt)} />
                <Fact label="Open for" value={lasted(ticket.createdAt, ticket.closedAt)} />
            {/if}
        </div>

        {#if transcript}
            <DiscordTranscript {transcript} topic={ticket.reason} {fileUrl} footer={people}>
                {#snippet aside()}
                    <Chip tone={statusTone[ticket.status]} size="sm">{statusName[ticket.status]}</Chip>
                    {#if loaded?.live}
                        <DiscordTooltip content="Load new messages">
                            <button
                                type="button"
                                disabled={refreshing}
                                class="flex size-8 cursor-pointer items-center justify-center rounded-full text-dc-icon hover:bg-white/10 hover:text-dc-strong disabled:opacity-50"
                                onclick={refresh}
                            >
                                <MaterialSymbolsRefreshRounded class={["size-5", refreshing && "animate-spin"]} />
                            </button>
                        </DiscordTooltip>
                    {/if}
                {/snippet}
            </DiscordTranscript>
        {:else}
            {#if loaded?.live}
                <EmptyState
                    tone="danger"
                    card
                    title="Couldn't read the messages"
                    text="Discord didn't hand this ticket's messages over just now."
                    retry={() => query?.refresh()}
                />
            {:else}
                <EmptyState
                    card
                    icon={MaterialSymbolsDescriptionRounded}
                    title="No transcript"
                    text="This ticket was deleted before Square started keeping transcripts on the dashboard."
                />
            {/if}
        {/if}
    {/if}
</div>
