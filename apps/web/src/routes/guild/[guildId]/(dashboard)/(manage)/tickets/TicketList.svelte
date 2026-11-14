<script lang="ts">
    import ConfirmDialog from "#lib/components/ConfirmDialog.svelte";
    import ResetButton from "#lib/components/ResetButton.svelte";
    import TableSkeleton from "#lib/components/TableSkeleton.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import Fact from "#lib/components/ui/Fact.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Pager from "#lib/components/ui/Pager.svelte";
    import PersonRow from "#lib/components/ui/PersonRow.svelte";
    import Segmented from "#lib/components/ui/Segmented.svelte";
    import DataTable from "#lib/components/ui/table/DataTable.svelte";
    import type { TableColumn } from "#lib/components/ui/table/features.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { Debounced } from "#lib/debounced.svelte.ts";
    import { getDetails } from "#lib/details.svelte.ts";
    import { errorMessage } from "#lib/errors.ts";
    import { dateTime, day, formatCount, plural } from "#lib/format.ts";
    import * as tickets from "#lib/tickets.remote.ts";
    import { statusName, statusTone } from "#lib/tickets.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import type { TicketDetail, TicketEntry } from "@square/api-client";
    import { renderSnippet, type SortingState } from "@tanstack/svelte-table";
    import MaterialSymbolsConfirmationNumberRounded from "~icons/material-symbols/confirmation-number-rounded";
    import MaterialSymbolsDeleteForeverRounded from "~icons/material-symbols/delete-forever-rounded";
    import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
    import MaterialSymbolsDescriptionRounded from "~icons/material-symbols/description-rounded";
    import MaterialSymbolsLockOpenRounded from "~icons/material-symbols/lock-open-rounded";
    import MaterialSymbolsLockRounded from "~icons/material-symbols/lock-rounded";
    import MaterialSymbolsOpenInNewRounded from "~icons/material-symbols/open-in-new-rounded";
    import MaterialSymbolsRefreshRounded from "~icons/material-symbols/refresh-rounded";
    import MaterialSymbolsSearchOffRounded from "~icons/material-symbols/search-off-rounded";
    import MaterialSymbolsSearchRounded from "~icons/material-symbols/search-rounded";

    let { guild, open = $bindable(0) }: { guild: string; open?: number } = $props();

    type Status = "open" | "closed" | "deleted" | "all";

    const details = getDetails();

    let status = $state<Status>("open");
    let typed = $state("");
    const search = new Debounced(() => typed.trim(), 300);
    const q = $derived(search.current);
    let page = $state(1);
    let sorting = $state<SortingState>([{ id: "number", desc: true }]);
    const order = $derived(sorting[0]?.desc === false ? "asc" : "desc");

    $effect.pre(() => {
        void q;
        page = 1;
    });

    const listQuery = $derived(tickets.ticketList({ guild, status, q, order, page }));
    const list = $derived(listQuery.current);

    $effect(() => {
        if (list) open = list.open;
    });

    const statusOptions = $derived<{ value: Status; label: string; count?: number }[]>([
        { value: "open", label: "Open", count: list?.open },
        { value: "closed", label: "Closed", count: list?.closed },
        { value: "deleted", label: "Deleted", count: list?.deleted },
        { value: "all", label: "All" },
    ]);

    const columns: TableColumn<TicketEntry>[] = [
        {
            id: "number",
            accessorKey: "number",
            header: "#",
            cell: ({ row }) => renderSnippet(labelCell, row.original),
            meta: { class: "w-24" },
        },
        { id: "opener", header: "Opened by", enableSorting: false, cell: ({ row }) => renderSnippet(openerCell, row.original) },
        {
            id: "reason",
            accessorKey: "reason",
            header: "Reason",
            enableSorting: false,
            cell: ({ row }) => renderSnippet(reasonCell, row.original),
            meta: { class: "hidden @3xl:table-cell" },
        },
        {
            id: "claimed",
            header: "Claimed by",
            enableSorting: false,
            cell: ({ row }) => row.original.claimedBy?.name ?? "Nobody",
            meta: { class: "hidden w-36 truncate text-gray-400 @5xl:table-cell" },
        },
        {
            id: "opened",
            header: "Opened",
            enableSorting: false,
            cell: ({ row }) => day.format(row.original.createdAt),
            meta: { class: "hidden w-32 text-gray-400 @2xl:table-cell" },
        },
        {
            id: "status",
            header: "Status",
            enableSorting: false,
            cell: ({ row }) => renderSnippet(statusCell, row.original),
            meta: { align: "end", class: "w-28" },
        },
        {
            id: "remove",
            header: "",
            enableSorting: false,
            cell: ({ row }) => renderSnippet(removeCell, row.original),
            meta: { align: "end", class: "w-14 pl-0" },
        },
    ];

    const KEY_PREFIX = "ticket:";
    const openNumber = $derived(details.key?.startsWith(KEY_PREFIX) ? Number(details.key.slice(KEY_PREFIX.length)) : null);
    const detailQuery = $derived(openNumber ? tickets.ticketDetail({ guild, number: openNumber }) : null);
    const detail = $derived(detailQuery?.current);

    const show = (entry: TicketEntry) => details.show(`Ticket ${entry.label}`, ticketPanel, `${KEY_PREFIX}${entry.number}`);

    function applied(next: TicketDetail) {
        detailQuery?.set(next);
        listQuery.refresh();
    }

    let reopening = $state(false);
    async function reopen(number: number) {
        reopening = true;
        try {
            applied(await tickets.reopenTicket({ guild, number }));
            toast.success("Ticket reopened");
        } catch (err) {
            toast.error(errorMessage(err, "Square couldn't reopen it. Try again."));
        } finally {
            reopening = false;
        }
    }

    type Purge = { title: string; description: string; label: string; done: string; run: () => Promise<unknown>; number?: number };
    let purge = $state<Purge>({ title: "", description: "", label: "Remove", done: "", run: async () => null });
    let purgeOpen = $state(false);

    function ask(next: Purge) {
        purge = next;
        purgeOpen = true;
    }

    const purgeOne = (entry: TicketEntry) =>
        ask({
            title: `Remove ticket ${entry.label} for good?`,
            description: "Its transcript and saved pictures go with it. This can't be undone.",
            label: "Remove for good",
            done: `Ticket ${entry.label} removed`,
            run: () => tickets.purgeTicket({ guild, number: entry.number }),
            number: entry.number,
        });

    const purgeAll = (count: number) =>
        ask({
            title: `Remove ${plural(count, "deleted ticket")} for good?`,
            description: "Every deleted ticket goes, with its transcript and saved pictures. This can't be undone.",
            label: "Remove all",
            done: "Deleted tickets removed",
            run: () => tickets.purgeDeletedTickets(guild),
        });

    function purged() {
        if (purge.number === undefined || purge.number === openNumber) details.close();
        listQuery.refresh();
    }
</script>

{#snippet labelCell(entry: TicketEntry)}
    <span class="font-mono font-semibold">{entry.label}</span>
{/snippet}

{#snippet openerCell(entry: TicketEntry)}
    <span class="flex min-w-0 items-center gap-4">
        <Avatar src={entry.opener.avatarUrl} name={entry.opener.name} class="size-8" />
        <span class="flex min-w-0 flex-col">
            <span class="truncate font-medium">{entry.opener.name}</span>
            <span class="truncate text-xs text-gray-400 @3xl:hidden">{entry.reason}</span>
        </span>
    </span>
{/snippet}

{#snippet reasonCell(entry: TicketEntry)}
    <span class="block truncate text-gray-400">{entry.reason}</span>
{/snippet}

{#snippet statusCell(entry: TicketEntry)}
    <Chip tone={statusTone[entry.status]} size="sm">{statusName[entry.status]}</Chip>
{/snippet}

{#snippet removeCell(entry: TicketEntry)}
    {#if !entry.channelId}
        <Tooltip content="Remove ticket {entry.label} for good">
            <Button
                variant="ghost-danger"
                size="sm"
                icon
                onclick={(event: MouseEvent) => {
                    event.stopPropagation();
                    purgeOne(entry);
                }}
                onkeydown={(event: KeyboardEvent) => event.stopPropagation()}
            >
                <MaterialSymbolsDeleteRounded />
            </Button>
        </Tooltip>
    {/if}
{/snippet}

{#snippet ticketPanel()}
    {#if detailQuery?.error}
        <EmptyState
            tone="danger"
            compact
            title="Couldn't load this ticket"
            text={detailQuery.error.message ?? "Square didn't answer. Try again in a moment."}
            retry={() => detailQuery.refresh()}
        />
    {:else if !detail}
        <div aria-label="Loading the ticket" aria-busy="true" class="flex flex-col gap-6">
            <div class="flex items-center gap-2">
                <span class="h-6 w-16 skeleton rounded-full"></span>
                <span class="h-3 w-24 skeleton rounded-full"></span>
            </div>
            <div class="flex flex-col gap-2">
                {#each [0, 1] as i (i)}
                    <div class="flex min-h-12 items-center gap-4 rounded-2xl bg-gray-800 p-2">
                        <span class="size-8 shrink-0 skeleton rounded-full"></span>
                        <span class="flex flex-1 flex-col gap-1.5">
                            <span class="h-3 w-16 skeleton rounded-full"></span>
                            <span class="h-3.5 w-28 skeleton rounded-full"></span>
                        </span>
                    </div>
                {/each}
            </div>
            <div class="grid grid-cols-2 gap-2">
                {#each [0, 1] as i (i)}
                    <div class="flex min-h-12 flex-col justify-center gap-1.5 rounded-2xl bg-gray-800 px-4 py-2">
                        <span class="h-3 w-12 skeleton rounded-full"></span>
                        <span class="h-3.5 w-24 skeleton rounded-full"></span>
                    </div>
                {/each}
            </div>
            <div class="flex flex-col gap-2">
                <span class="h-4 w-16 skeleton rounded-full"></span>
                <div class="flex flex-col gap-2 rounded-2xl bg-gray-800 p-4">
                    <span class="h-3.5 w-4/5 skeleton rounded-full"></span>
                    <span class="h-3.5 w-1/2 skeleton rounded-full"></span>
                </div>
            </div>
            <span class="h-12 skeleton rounded-full md:h-10"></span>
        </div>
    {:else}
        <div class="flex flex-col gap-6">
            <div class="flex flex-wrap items-center gap-2">
                <Chip tone={statusTone[detail.status]} size="sm">{statusName[detail.status]}</Chip>
                {#if detail.channelName}<span class="truncate font-mono text-xs text-gray-400">#{detail.channelName}</span>{/if}
            </div>

            <div class="flex flex-col gap-2">
                <PersonRow label="Opened by" person={detail.opener} />
                <PersonRow label="Claimed by" person={detail.claimedBy} />
                {#if detail.status !== "open"}<PersonRow label="Closed by" person={detail.closedBy} />{/if}
            </div>

            <div class="grid grid-cols-2 gap-2">
                <Fact label="Opened" value={dateTime.format(detail.createdAt)} />
                <Fact label="Closed" value={detail.closedAt ? dateTime.format(detail.closedAt) : "Still open"} />
            </div>

            <div class="flex flex-col gap-2">
                <h3 class="text-sm font-medium">Reason</h3>
                <p class="rounded-2xl bg-gray-800 p-4 text-sm wrap-anywhere whitespace-pre-wrap text-gray-200">{detail.reason}</p>
            </div>

            {#if detail.people.length}
                <div class="flex flex-col gap-2">
                    <h3 class="text-sm font-medium">In this ticket</h3>
                    <ul class="flex flex-wrap gap-2">
                        {#each detail.people as member (member.id)}
                            <li>
                                <Chip class="pl-1">
                                    <Avatar src={member.avatarUrl} name={member.name} class="size-6" />
                                    <span class="max-w-40 truncate">{member.name}</span>
                                </Chip>
                            </li>
                        {/each}
                    </ul>
                </div>
            {/if}

            <div class="flex flex-col gap-2">
                {#if detail.messages !== null || detail.channelId}
                    <Button href="/guild/{guild}/tickets/{detail.number}">
                        <MaterialSymbolsDescriptionRounded />Show transcript{#if detail.messages !== null}<span class="text-gray-400"
                                >· {plural(detail.messages, "message")}</span
                            >{/if}
                    </Button>
                {/if}
                {#if detail.channelId}
                    <Button variant="ghost" href="https://discord.com/channels/{guild}/{detail.channelId}" target="_blank" rel="noopener">
                        <MaterialSymbolsOpenInNewRounded />Open in Discord
                    </Button>
                {/if}
            </div>

            {#if detail.channelId && detail.status !== "deleted"}
                <div class="flex flex-wrap gap-2 *:flex-1">
                    {#if detail.status === "open"}
                        <ResetButton
                            title="Close ticket {detail.label}?"
                            description="Square saves the transcript and hides the channel from the opener and added members."
                            label="Close"
                            busy="Closing…"
                            done="Ticket closed"
                            icon={MaterialSymbolsLockRounded}
                            reset={() => tickets.closeTicket({ guild, number: detail.number })}
                            apply={applied}
                        />
                    {:else}
                        <Button loading={reopening} onclick={() => reopen(detail.number)}>
                            {#if !reopening}<MaterialSymbolsLockOpenRounded />{/if}{reopening ? "Reopening…" : "Reopen"}
                        </Button>
                    {/if}
                    <ResetButton
                        title="Delete ticket {detail.label}?"
                        description="Square saves the transcript one last time and deletes the ticket's channel. The ticket and its transcript stay here until you remove them for good."
                        label="Delete"
                        busy="Deleting…"
                        done="Ticket deleted"
                        variant="danger"
                        icon={MaterialSymbolsDeleteRounded}
                        reset={() => tickets.deleteTicket({ guild, number: detail.number })}
                        apply={applied}
                    />
                </div>
            {:else if !detail.channelId}
                {#if detail.status !== "deleted"}
                    <p class="text-sm text-gray-400">This ticket's channel was deleted outside Square, so it can't be closed or reopened here.</p>
                {/if}
                <Button variant="danger" onclick={() => purgeOne(detail)}><MaterialSymbolsDeleteForeverRounded />Remove for good</Button>
            {/if}
        </div>
    {/if}
{/snippet}

<div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center gap-2">
        <Segmented
            label="Ticket status"
            options={statusOptions}
            bind:value={
                () => status,
                (next) => {
                    status = next;
                    page = 1;
                }
            }
        />
        <Input
            type="search"
            icon={MaterialSymbolsSearchRounded}
            placeholder="Search number, reason or opener"
            aria-label="Search tickets"
            bind:value={typed}
            class="min-w-60 flex-1"
        />
        <Tooltip content="Refresh tickets">
            <Button variant="ghost" icon onclick={() => listQuery.refresh()}>
                <MaterialSymbolsRefreshRounded />
            </Button>
        </Tooltip>
        {#if status === "deleted" && list?.deleted}
            <Button variant="danger" onclick={() => purgeAll(list.deleted)}><MaterialSymbolsDeleteForeverRounded />Delete all</Button>
        {/if}
    </div>

    {#if listQuery.error}
        <EmptyState
            tone="danger"
            card
            title="Couldn't load the tickets"
            text={listQuery.error.message ?? "Square didn't answer. Try again in a moment."}
            retry={() => listQuery.refresh()}
        />
    {:else if !list}
        <TableSkeleton />
    {:else if !list.entries.length}
        <EmptyState
            card
            icon={q ? MaterialSymbolsSearchOffRounded : MaterialSymbolsConfirmationNumberRounded}
            title={q ? "No matches" : "No tickets"}
            text={q ? "No tickets match that search." : status === "open" ? "No open tickets right now." : "No tickets here yet."}
        />
    {:else}
        <DataTable
            label="Tickets"
            data={list.entries}
            {columns}
            getRowId={(entry) => String(entry.number)}
            manualSorting
            bind:sorting={
                () => sorting,
                (next) => {
                    sorting = next;
                    page = 1;
                }
            }
            active={openNumber ? String(openNumber) : null}
            onrowclick={show}
        />
        <div class="flex items-center justify-end gap-2">
            <span class="text-sm text-gray-400">{formatCount(list.total)} {list.total === 1 ? "ticket" : "tickets"}</span>
            <Pager page={list.page} pages={list.pages} onpage={(next) => (page = next)} />
        </div>
    {/if}
</div>

<ConfirmDialog
    bind:open={purgeOpen}
    title={purge.title}
    description={purge.description}
    label={purge.label}
    busy="Removing…"
    done={purge.done}
    run={purge.run}
    apply={purged}
/>
