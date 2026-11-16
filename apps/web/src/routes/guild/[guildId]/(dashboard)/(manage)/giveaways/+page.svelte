<script lang="ts">
    import PageHeading from "#lib/components/dashboard/PageHeading.svelte";
    import TableSkeleton from "#lib/components/dashboard/TableSkeleton.svelte";
    import Mention from "#lib/components/discord/Mention.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Pager from "#lib/components/ui/Pager.svelte";
    import Segmented from "#lib/components/ui/Segmented.svelte";
    import DataTable from "#lib/components/ui/table/DataTable.svelte";
    import type { TableColumn } from "#lib/components/ui/table/features.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { now } from "#lib/discord/now.svelte.ts";
    import { formatCount, plural } from "#lib/format.ts";
    import { Debounced } from "#lib/reactive/debounced.svelte.ts";
    import { refetch } from "#lib/refetch.ts";
    import * as settings from "#lib/settings/settings.remote.ts";
    import { afterNavigate, goto } from "$app/navigation";
    import type { GiveawaySummary } from "@square/api-client";
    import { renderSnippet } from "@tanstack/svelte-table";
    import { untrack } from "svelte";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import MaterialSymbolsCelebrationRounded from "~icons/material-symbols/celebration-rounded";
    import MaterialSymbolsRefreshRounded from "~icons/material-symbols/refresh-rounded";
    import MaterialSymbolsSearchOffRounded from "~icons/material-symbols/search-off-rounded";
    import MaterialSymbolsSearchRounded from "~icons/material-symbols/search-rounded";
    import type { PageProps } from "./$types";
    import { statusName, statusTone, whenText } from "./giveaway.ts";
    import * as giveaways from "./giveaways.remote.ts";

    let { data }: PageProps = $props();

    type Status = "running" | "scheduled" | "ended" | "all";

    const guild = $derived(data.guild.id);
    let status = $state<Status>("all");
    let typed = $state("");
    const search = new Debounced(() => typed.trim(), 300);
    const q = $derived(search.current);
    let page = $state(1);

    const listQuery = $derived(giveaways.giveawayList({ guild, status, q, page }));
    const list = $derived(listQuery.current);
    const channelsQuery = $derived(settings.guildChannels(guild));
    const channelName = (id: string) => channelsQuery.current?.find((channel) => channel.id === id)?.name ?? "deleted-channel";
    const revisit = () => refetch(() => listQuery);
    afterNavigate(revisit);

    let searched: string | undefined;
    $effect.pre(() => {
        page = 1;
        if (searched !== undefined && searched !== q) untrack(revisit);
        searched = q;
    });

    const statusOptions = $derived<{ value: Status; label: string; count?: number }[]>([
        { value: "all", label: "All" },
        { value: "running", label: "Running", count: list?.running },
        { value: "scheduled", label: "Scheduled", count: list?.scheduled },
        { value: "ended", label: "Ended", count: list?.ended },
    ]);

    const columns: TableColumn<GiveawaySummary>[] = [
        { id: "prize", header: "Prize", enableSorting: false, cell: ({ row }) => renderSnippet(prizeCell, row.original) },
        {
            id: "entries",
            header: "Entries",
            enableSorting: false,
            cell: ({ row }) => formatCount(row.original.entries),
            meta: { align: "end", class: "hidden w-24 font-mono text-gray-400 @2xl:table-cell" },
        },
        {
            id: "winners",
            header: "Winners",
            enableSorting: false,
            cell: ({ row }) => formatCount(row.original.winnerCount),
            meta: { align: "end", class: "hidden w-24 font-mono text-gray-400 @3xl:table-cell" },
        },
        {
            id: "when",
            header: "When",
            enableSorting: false,
            cell: ({ row }) => whenText(row.original, now.current),
            meta: { class: "hidden w-44 text-gray-400 @3xl:table-cell" },
        },
        {
            id: "status",
            header: "Status",
            enableSorting: false,
            cell: ({ row }) => renderSnippet(statusCell, row.original),
            meta: { align: "end", class: "w-32" },
        },
    ];
</script>

{#snippet prizeCell(entry: GiveawaySummary)}
    <span class="flex min-w-0 flex-col gap-1">
        <span class="truncate font-medium">{entry.prize}</span>
        <span class="flex min-w-0 items-center gap-2 text-xs text-gray-400">
            <Mention kind="channel" name={channelName(entry.channelId)} />
            <span class="truncate @3xl:hidden"
                >{whenText(entry, now.current)} · {formatCount(entry.entries)} {entry.entries === 1 ? "entry" : "entries"}</span
            >
        </span>
    </span>
{/snippet}

{#snippet statusCell(entry: GiveawaySummary)}
    {#if entry.status === "ended" && !entry.posted}
        <Tooltip content="Square couldn't post it, or its message was deleted">
            <Chip tone="danger" size="sm">Not posted</Chip>
        </Tooltip>
    {:else}
        <Chip tone={statusTone[entry.status]} size="sm">{statusName[entry.status]}</Chip>
    {/if}
{/snippet}

<div class="flex flex-col gap-6">
    <PageHeading title="Giveaways" description="Run giveaways in {data.guild.name} that pick fair winners right on time.">
        {#snippet actions()}
            <Button variant="primary" href="/guild/{guild}/giveaways/new"><MaterialSymbolsAddRounded />New giveaway</Button>
        {/snippet}
    </PageHeading>

    <div class="flex flex-col gap-4">
        <div class="flex flex-wrap items-center gap-2">
            <Segmented
                label="Giveaway status"
                options={statusOptions}
                bind:value={
                    () => status,
                    (next) => {
                        status = next;
                        page = 1;
                        revisit();
                    }
                }
            />
            <Input
                type="search"
                icon={MaterialSymbolsSearchRounded}
                placeholder="Search prizes"
                aria-label="Search giveaways"
                bind:value={typed}
                class="min-w-60 flex-1"
            />
            <Tooltip content="Refresh giveaways">
                <Button variant="ghost" icon onclick={() => listQuery.refresh()}>
                    <MaterialSymbolsRefreshRounded />
                </Button>
            </Tooltip>
        </div>

        {#if listQuery.error}
            <EmptyState
                tone="danger"
                card
                title="Couldn't load the giveaways"
                text={listQuery.error.message ?? "Square didn't answer. Try again in a moment."}
                retry={() => listQuery.refresh()}
            />
        {:else if !list || !channelsQuery.current}
            <TableSkeleton toolbar="filter" />
        {:else if !list.items.length}
            <EmptyState
                card
                icon={q ? MaterialSymbolsSearchOffRounded : MaterialSymbolsCelebrationRounded}
                title={q
                    ? "No matches"
                    : status === "all"
                      ? "No giveaways yet"
                      : `No ${statusName[status as Exclude<Status, "all">].toLowerCase()} giveaways`}
            >
                {#if q}No giveaway prizes match that search.{:else}Start one here, or with <Mention kind="command" name="giveaway start" /> in Discord.{/if}
            </EmptyState>
        {:else}
            <DataTable
                label="Giveaways"
                data={list.items}
                {columns}
                getRowId={(entry) => String(entry.id)}
                onrowclick={(entry) => goto(`/guild/${guild}/giveaways/${entry.id}`)}
            />
            <div class="flex items-center justify-end gap-2">
                <span class="text-sm text-gray-400">{plural(list.total, "giveaway")}</span>
                <Pager
                    page={list.page}
                    pages={list.pages}
                    onpage={(next) => {
                        page = next;
                        revisit();
                    }}
                />
            </div>
        {/if}
    </div>
</div>
