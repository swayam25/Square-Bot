<script lang="ts">
    import { getDetails } from "#lib/components/dashboard/details.svelte.ts";
    import ResetButton from "#lib/components/dashboard/ResetButton.svelte";
    import TableSkeleton from "#lib/components/dashboard/TableSkeleton.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import Fact from "#lib/components/ui/Fact.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Pager from "#lib/components/ui/Pager.svelte";
    import DataTable from "#lib/components/ui/table/DataTable.svelte";
    import type { TableColumn } from "#lib/components/ui/table/features.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { now } from "#lib/discord/now.svelte.ts";
    import { errorMessage } from "#lib/errors.ts";
    import { dateTime, formatCount } from "#lib/format.ts";
    import { Debounced } from "#lib/reactive/debounced.svelte.ts";
    import { refetch } from "#lib/refetch.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { afterNavigate } from "$app/navigation";
    import type { Entrant, Giveaway } from "@square/api-client";
    import { renderSnippet, type RowSelectionState, type SortingState } from "@tanstack/svelte-table";
    import { untrack } from "svelte";
    import MaterialSymbolsAddCircleRounded from "~icons/material-symbols/add-circle-rounded";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";
    import MaterialSymbolsGroupRounded from "~icons/material-symbols/group-rounded";
    import MaterialSymbolsPersonRemoveRounded from "~icons/material-symbols/person-remove-rounded";
    import MaterialSymbolsRefreshRounded from "~icons/material-symbols/refresh-rounded";
    import MaterialSymbolsSearchOffRounded from "~icons/material-symbols/search-off-rounded";
    import MaterialSymbolsSearchRounded from "~icons/material-symbols/search-rounded";
    import { LIMITS, relative } from "../giveaway.ts";
    import * as giveaways from "../giveaways.remote.ts";

    let { guild, giveaway, onchange }: { guild: string; giveaway: Giveaway; onchange: () => void } = $props();

    const details = getDetails();
    const id = $derived(giveaway.id);
    const frozen = $derived(giveaway.status === "ended" ? "Entries can't change once the giveaway has ended" : null);

    let typed = $state("");
    const search = new Debounced(() => typed.trim(), 300);
    const q = $derived(search.current);
    let page = $state(1);
    let sorting = $state<SortingState>([{ id: "entered", desc: true }]);
    const sort = $derived((sorting[0]?.id ?? "entered") as "entered" | "entries");
    const order = $derived(sorting[0]?.desc === false ? "asc" : "desc");

    const listQuery = $derived(giveaways.entrantList({ guild, id, q, sort, order, page }));
    const list = $derived(listQuery.current);
    const revisit = () => refetch(() => listQuery);
    afterNavigate(revisit);

    let searched: string | undefined;
    $effect.pre(() => {
        page = 1;
        if (searched !== undefined && searched !== q) untrack(revisit);
        searched = q;
    });

    let selection = $state<RowSelectionState>({});
    const picked = $derived(Object.keys(selection).filter((key) => selection[key]));
    $effect(() => {
        void page;
        void q;
        selection = {};
    });

    const percent = (chance: number) => (chance >= 0.001 || chance === 0 ? `${(chance * 100).toFixed(1)}%` : "<0.1%");
    const entriesText = (count: number) => `${formatCount(count)} ${count === 1 ? "entry" : "entries"}`;

    const columns: TableColumn<Entrant>[] = [
        { id: "person", header: "Person", enableSorting: false, cell: ({ row }) => renderSnippet(personCell, row.original) },
        {
            id: "entries",
            accessorKey: "entries",
            header: "Entries",
            cell: ({ row }) => renderSnippet(entriesCell, row.original),
            meta: { align: "end", class: "w-28" },
        },
        {
            id: "odds",
            header: "Odds",
            enableSorting: false,
            cell: ({ row }) => percent(row.original.chance),
            meta: { align: "end", class: "hidden w-24 font-mono text-gray-400 @2xl:table-cell" },
        },
        {
            id: "entered",
            accessorKey: "enteredAt",
            header: "Entered",
            cell: ({ row }) => relative(row.original.enteredAt, now.current),
            meta: { class: "hidden w-36 text-gray-400 @3xl:table-cell" },
        },
    ];

    const KEY = "entrant:";
    const BULK = "entrants:bulk";
    const openId = $derived(details.key?.startsWith(KEY) ? details.key.slice(KEY.length) : null);
    const opened = $derived(list?.items.find((entry) => entry.user.id === openId) ?? null);

    function show(entry: Entrant) {
        extra = entry.bonus;
        details.show("Entrant", entrantPanel, `${KEY}${entry.user.id}`);
    }

    let extra = $state<number | null>(0);
    let bulkExtra = $state<number | null>(1);
    let saving = $state(false);
    const validExtra = (value: number | null) => Number.isInteger(value) && value! >= 0 && value! <= LIMITS.entries;

    async function setExtra(userIds: string[], bonus: number) {
        saving = true;
        try {
            await giveaways.setEntrantBonus({ guild, id, userIds, bonus }).updates(listQuery);
            toast.success(userIds.length === 1 ? "Extra entries saved" : `Extra entries saved for ${formatCount(userIds.length)} people`);
            return true;
        } catch (err) {
            toast.error(errorMessage(err, "Square couldn't change the entries. Try again."));
            return false;
        } finally {
            saving = false;
        }
    }

    function openBulk() {
        bulkExtra = 1;
        details.show("Extra entries", bulkPanel, BULK);
    }

    const removeOne = (entry: Entrant) => giveaways.removeEntrants({ guild, id, userIds: [entry.user.id] }).updates(listQuery);
    const removePicked = () => giveaways.removeEntrants({ guild, id, userIds: picked }).updates(listQuery);
</script>

{#snippet personCell(entry: Entrant)}
    <span class="flex min-w-0 items-center gap-4">
        <Avatar src={entry.user.avatarUrl} name={entry.user.name} class="size-8" />
        <span class="flex min-w-0 flex-col">
            <span class="flex min-w-0 items-center gap-2">
                <span class="truncate font-medium">{entry.user.name}</span>
                {#if entry.winner}<Chip tone="warning" size="sm">Winner</Chip>{/if}
                {#if !entry.member}
                    <Chip tone="muted" size="sm">Left</Chip>
                {:else if !entry.eligible}
                    <Tooltip content="They no longer meet the requirements, so the draw skips them">
                        <Chip tone="danger" size="sm">Can't win</Chip>
                    </Tooltip>
                {/if}
            </span>
            <span class="truncate text-xs text-gray-400 @2xl:hidden">{percent(entry.chance)} odds · {relative(entry.enteredAt, now.current)}</span>
        </span>
    </span>
{/snippet}

{#snippet entriesCell(entry: Entrant)}
    <span class="font-display text-lg font-semibold">{formatCount(entry.entries)}</span>
{/snippet}

{#snippet bulkPanel()}
    <div class="flex flex-col gap-6">
        <p class="text-sm text-gray-400">
            Everyone gets 1 entry. Extra entries go on top, alongside any bonus from their roles. Setting them replaces what each person had.
        </p>
        <div class="flex flex-col gap-2">
            <h3 class="text-sm font-medium">Extra entries for {formatCount(picked.length)} {picked.length === 1 ? "person" : "people"}</h3>
            <Input
                type="number"
                min={0}
                max={LIMITS.entries}
                step={1}
                aria-label="Extra entries"
                error={bulkExtra === null || validExtra(bulkExtra) ? null : `Pick 0 to ${LIMITS.entries}`}
                bind:value={bulkExtra}
            />
        </div>
        <Button
            variant="primary"
            loading={saving}
            disabled={!picked.length || !validExtra(bulkExtra)}
            onclick={async () => {
                if (await setExtra(picked, bulkExtra!)) {
                    selection = {};
                    details.close();
                }
            }}
        >
            {saving ? "Saving…" : "Apply"}
        </Button>
    </div>
{/snippet}

{#snippet entrantPanel()}
    {#if !opened}
        <EmptyState compact icon={MaterialSymbolsGroupRounded} title="Not on this page" text="Find them in the table again to see their entries." />
    {:else}
        <div class="flex flex-col gap-6">
            <div class="flex items-center gap-4">
                <Avatar src={opened.user.avatarUrl} name={opened.user.name} class="size-14" />
                <div class="flex min-w-0 flex-col gap-1">
                    <span class="flex min-w-0 items-center gap-2">
                        <span class="truncate font-medium">{opened.user.name}</span>
                        {#if opened.winner}<Chip tone="warning" size="sm">Winner</Chip>{/if}
                    </span>
                    <span class="truncate font-mono text-xs text-gray-400">{opened.user.id}</span>
                </div>
            </div>

            <div class="grid grid-cols-2 gap-2">
                <Fact size="lg" label="Entries" value={formatCount(opened.entries)} accent />
                <Fact size="lg" label="Odds" value={percent(opened.chance)} />
                <Fact size="lg" label="From roles" value="+{formatCount(opened.roleBonus)}" />
                <Fact size="lg" label="Extra" value="+{formatCount(opened.bonus)}" />
            </div>
            <Fact label="Entered" value={dateTime.format(opened.enteredAt)} />
            {#if !opened.member || !opened.eligible}
                <p class="rounded-2xl bg-gray-800 p-4 text-sm text-gray-300">
                    {opened.member
                        ? "They no longer meet this giveaway's requirements, so the draw skips them."
                        : "They left the server, so the draw skips them."}
                </p>
            {/if}

            <div class="flex flex-col gap-2">
                <h3 class="text-sm font-medium">Extra entries</h3>
                <div class="flex items-center gap-2">
                    <Tooltip content={frozen} class="flex-1">
                        <Input
                            type="number"
                            min={0}
                            max={LIMITS.entries}
                            step={1}
                            aria-label="Extra entries"
                            disabled={!!frozen}
                            error={extra === null || validExtra(extra) ? null : `Pick 0 to ${LIMITS.entries}`}
                            bind:value={extra}
                        />
                    </Tooltip>
                    <Button
                        variant="primary"
                        loading={saving}
                        disabled={!!frozen || !validExtra(extra) || extra === opened.bonus}
                        onclick={() => setExtra([opened.user.id], extra!)}
                    >
                        {saving ? "Saving…" : "Save"}
                    </Button>
                </div>
            </div>

            <Tooltip content={frozen} class="w-full">
                <ResetButton
                    title="Remove {opened.user.name} from the giveaway?"
                    description="Their entries go, and they can't win unless they enter again."
                    label="Remove from giveaway"
                    busy="Removing…"
                    done="{opened.user.name} removed"
                    variant="danger"
                    icon={MaterialSymbolsPersonRemoveRounded}
                    disabled={!!frozen}
                    reset={() => removeOne(opened)}
                    apply={() => {
                        details.close();
                        onchange();
                    }}
                />
            </Tooltip>
        </div>
    {/if}
{/snippet}

<div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center gap-2">
        <Input
            type="search"
            icon={MaterialSymbolsSearchRounded}
            placeholder="Search by name or ID"
            aria-label="Search entrants"
            bind:value={typed}
            class="min-w-60 flex-1"
        />
        {#if picked.length}
            <span class="px-2 text-sm whitespace-nowrap text-gray-400">{formatCount(picked.length)} picked</span>
            <Tooltip content={frozen}>
                <Button disabled={!!frozen} onclick={openBulk}><MaterialSymbolsAddCircleRounded />Extra entries</Button>
            </Tooltip>
            <Tooltip content={frozen}>
                <ResetButton
                    title="Remove {formatCount(picked.length)} {picked.length === 1 ? 'person' : 'people'}?"
                    description="Their entries go, and they can't win unless they enter again."
                    label="Remove"
                    busy="Removing…"
                    done="Removed from the giveaway"
                    variant="danger"
                    icon={MaterialSymbolsPersonRemoveRounded}
                    disabled={!!frozen}
                    reset={removePicked}
                    apply={() => {
                        selection = {};
                        if (details.key === BULK) details.close();
                        onchange();
                    }}
                />
            </Tooltip>
            <Tooltip content="Clear selection">
                <Button variant="ghost" icon onclick={() => (selection = {})}><MaterialSymbolsCloseRounded /></Button>
            </Tooltip>
        {:else}
            <Tooltip content="Refresh entrants">
                <Button variant="ghost" icon onclick={() => listQuery.refresh()}><MaterialSymbolsRefreshRounded /></Button>
            </Tooltip>
        {/if}
    </div>

    {#if listQuery.error}
        <EmptyState
            tone="danger"
            card
            title="Couldn't load the entrants"
            text={listQuery.error.message ?? "Square didn't answer. Try again in a moment."}
            retry={() => listQuery.refresh()}
        />
    {:else if !list}
        <TableSkeleton toolbar="search" />
    {:else if !list.items.length}
        <EmptyState
            card
            icon={q ? MaterialSymbolsSearchOffRounded : MaterialSymbolsGroupRounded}
            title={q ? "No matches" : "Nobody yet"}
            text={q
                ? "Nobody in this giveaway matches that."
                : giveaway.status === "scheduled"
                  ? "People can enter once it starts."
                  : giveaway.status === "running"
                    ? "Nobody has entered yet."
                    : "Nobody entered this giveaway."}
        />
    {:else}
        <DataTable
            label="Entrants"
            data={list.items}
            {columns}
            getRowId={(entry) => entry.user.id}
            manualSorting
            selectable={!frozen}
            bind:rowSelection={selection}
            bind:sorting={
                () => sorting,
                (next) => {
                    sorting = next;
                    page = 1;
                    revisit();
                }
            }
            active={openId}
            onrowclick={show}
        />
        <div class="flex flex-wrap items-center justify-end gap-2">
            <span class="text-sm text-gray-400">
                {formatCount(list.people)}
                {list.people === 1 ? "person" : "people"} · {entriesText(list.tickets)} in the draw
            </span>
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
