<script lang="ts">
    import PageHeading from "#lib/components/PageHeading.svelte";
    import PageSkeleton from "#lib/components/PageSkeleton.svelte";
    import QueryGate from "#lib/components/QueryGate.svelte";
    import ResetButton from "#lib/components/ResetButton.svelte";
    import SaveBar from "#lib/components/SaveBar.svelte";
    import SettingGroup from "#lib/components/SettingGroup.svelte";
    import SettingRow from "#lib/components/SettingRow.svelte";
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
    import Tabs from "#lib/components/ui/Tabs.svelte";
    import UserPicker from "#lib/components/UserPicker.svelte";
    import { getDetails } from "#lib/details.svelte.ts";
    import { errorMessage } from "#lib/errors.ts";
    import { day, formatCount } from "#lib/format.ts";
    import * as invites from "#lib/invites.remote.ts";
    import * as settings from "#lib/settings.remote.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import type { InviteEntry, Person } from "@square/api-client";
    import { renderSnippet, type RowSelectionState, type SortingState } from "@tanstack/svelte-table";
    import MaterialSymbolsAddCircleRounded from "~icons/material-symbols/add-circle-rounded";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";
    import MaterialSymbolsGroupAddRounded from "~icons/material-symbols/group-add-rounded";
    import MaterialSymbolsLeaderboardRounded from "~icons/material-symbols/leaderboard-rounded";
    import MaterialSymbolsNoAccountsRounded from "~icons/material-symbols/no-accounts-rounded";
    import MaterialSymbolsTuneRounded from "~icons/material-symbols/tune-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    const MAX_FAKE_DAYS = 365;
    const DEFAULT_FAKE_DAYS = 7;
    const MAX_BONUS = 100_000;
    const MAX_BONUS_PEOPLE = 100;

    type Mode = "add" | "set";
    const MODES: { value: Mode; label: string }[] = [
        { value: "add", label: "Add" },
        { value: "set", label: "Set to" },
    ];

    const details = getDetails();
    const guild = $derived(data.guild.id);
    const savedQuery = $derived(settings.inviteSettings(guild));
    const saved = $derived(savedQuery.current!);

    let tab = $state<"leaderboard" | "settings">("leaderboard");

    type SortKey = "total" | "regular" | "left" | "fake" | "bonus";
    let page = $state(1);
    let sorting = $state<SortingState>([{ id: "total", desc: true }]);
    const sort = $derived((sorting[0]?.id ?? "total") as SortKey);
    const order = $derived(sorting[0] && !sorting[0].desc ? "asc" : "desc");
    const boardQuery = $derived(invites.inviteLeaderboard({ guild, page, sort, order }));
    const board = $derived(boardQuery.current);

    let fakeDays = $derived<number | null>(saved.fakeDays);
    const validDays = $derived(Number.isInteger(fakeDays) && fakeDays! >= 0 && fakeDays! <= MAX_FAKE_DAYS);
    const changes = $derived({ ...(fakeDays !== saved.fakeDays && { fakeDays: fakeDays! }) });

    let picked = $state<Person[]>([]);
    const isPicked = (id: string) => picked.some((person) => person.id === id);
    const pick = (person: Person, on: boolean) =>
        (picked = on ? (isPicked(person.id) ? picked : [...picked, person]) : picked.filter((other) => other.id !== person.id));

    const selection: RowSelectionState = $derived(Object.fromEntries(picked.map((person) => [person.id, true])));
    function select(next: RowSelectionState) {
        const onPage = new Map((board?.entries ?? []).map((entry) => [entry.user.id, entry.user]));
        picked = [
            ...picked.filter((person) => !onPage.has(person.id) || next[person.id]),
            ...[...onPage.values()].filter((person) => next[person.id] && !isPicked(person.id)),
        ];
    }

    const countColumn = (key: SortKey, header: string): TableColumn<InviteEntry> => ({
        id: key,
        accessorKey: key,
        header,
        cell: ({ getValue }) => formatCount(getValue()),
        meta: { align: "end", class: "hidden w-20 font-mono text-gray-400 @2xl:table-cell" },
    });
    const columns: TableColumn<InviteEntry>[] = [
        { id: "rank", header: "#", enableSorting: false, cell: ({ row }) => renderSnippet(rankCell, row.original), meta: { class: "w-12" } },
        { id: "member", header: "Member", enableSorting: false, cell: ({ row }) => renderSnippet(memberCell, row.original) },
        countColumn("regular", "Regular"),
        countColumn("left", "Left"),
        countColumn("fake", "Fake"),
        countColumn("bonus", "Bonus"),
        {
            id: "total",
            accessorKey: "total",
            header: "Total",
            cell: ({ row }) => renderSnippet(totalCell, row.original),
            meta: { align: "end", class: "w-20" },
        },
    ];

    const validAmount = (amount: number | null, mode: Mode) =>
        Number.isInteger(amount) && Math.abs(amount!) <= MAX_BONUS && (mode === "set" || amount !== 0);

    async function giveBonus(userIds: string[], amount: number, mode: Mode) {
        await invites.changeBonus({ guild, userIds, amount, mode });
        await Promise.all([boardQuery.refresh(), profileQuery?.refresh()]);
    }

    const open = (person: Person) => details.show("Invites", profilePanel, person.id);

    const BULK = "bonus";
    const profileKey = $derived(details.key && details.key !== BULK ? details.key : null);
    const profileQuery = $derived(profileKey ? invites.inviteProfile({ guild, user: profileKey }) : null);
    const profile = $derived(profileQuery?.current);
    let panelMode = $state<Mode>("add");
    let panelAmount = $state<number | null>(null);
    let panelBusy = $state(false);

    $effect(() => {
        void details.key;
        panelAmount = null;
        panelMode = "add";
    });

    async function applyPanelBonus() {
        if (!profile || !validAmount(panelAmount, panelMode)) return;
        panelBusy = true;
        try {
            await giveBonus([profile.user.id], panelAmount!, panelMode);
            panelAmount = null;
            toast.success(`Bonus invites updated for ${profile.user.name}`);
        } catch (err) {
            toast.error(errorMessage(err, "Square couldn't change the bonus. Try again."));
        } finally {
            panelBusy = false;
        }
    }

    let bulkMode = $state<Mode>("add");
    let bulkAmount = $state<number | null>(null);
    let bulkBusy = $state(false);

    function openBulk() {
        bulkMode = "add";
        bulkAmount = null;
        details.show("Give bonus", bulkPanel, BULK);
    }

    async function applyBulk() {
        bulkBusy = true;
        const count = picked.length;
        try {
            await giveBonus(
                picked.map((person) => person.id),
                bulkAmount!,
                bulkMode,
            );
            picked = [];
            bulkAmount = null;
            details.close();
            toast.success(`Bonus invites updated for ${people(count)}`);
        } catch (err) {
            toast.error(errorMessage(err, "Square couldn't change the bonuses. Try again."));
        } finally {
            bulkBusy = false;
        }
    }

    const people = (count: number) => (count === 1 ? "1 person" : `${formatCount(count)} people`);
    const rankTone = (rank: number) =>
        rank === 1 ? "text-amber-300" : rank === 2 ? "text-gray-200" : rank === 3 ? "text-orange-300" : "text-gray-400";
</script>

{#snippet amountField(mode: Mode, setMode: (mode: Mode) => void, amount: number | null, setAmount: (value: number | null) => void)}
    <div class="flex flex-col gap-2">
        <Segmented label="Bonus mode" options={MODES} bind:value={() => mode, setMode} />
        <Input
            type="number"
            min={-MAX_BONUS}
            max={MAX_BONUS}
            step={1}
            placeholder={mode === "add" ? "Amount, negative takes away" : "New bonus"}
            aria-label="Bonus amount"
            invalid={amount !== null && !validAmount(amount, mode)}
            bind:value={() => amount, setAmount}
        />
    </div>
{/snippet}

{#snippet rankCell(entry: InviteEntry)}
    <span class={["font-mono font-semibold", rankTone(entry.rank)]}>{formatCount(entry.rank)}</span>
{/snippet}

{#snippet memberCell(entry: InviteEntry)}
    <span class="flex min-w-0 items-center gap-4">
        <Avatar src={entry.user.avatarUrl} name={entry.user.name} class="size-8" />
        <span class="flex min-w-0 flex-col">
            <span class="truncate font-medium">{entry.user.name}</span>
            <span class="truncate text-xs text-gray-400 @2xl:hidden">
                {formatCount(entry.regular)} regular · {formatCount(entry.left)} left · {formatCount(entry.fake)} fake · {formatCount(entry.bonus)} bonus
            </span>
        </span>
    </span>
{/snippet}

{#snippet totalCell(entry: InviteEntry)}
    <span class="font-display text-lg font-semibold">{formatCount(entry.total)}</span>
{/snippet}

{#snippet bulkPanel()}
    <div class="flex flex-col gap-6">
        <div class="flex flex-col gap-2">
            <h3 class="text-sm font-medium">People</h3>
            {#if picked.length < MAX_BONUS_PEOPLE}
                <UserPicker {guild} title="Add a person" humansOnly exclude={picked.map((person) => person.id)} onpick={(user) => pick(user, true)} />
            {/if}
            {#if picked.length}
                <ul class="flex flex-wrap gap-2">
                    {#each picked as person (person.id)}
                        <li>
                            <Chip class="pl-1" remove={{ label: `Remove ${person.name}`, onclick: () => pick(person, false) }}>
                                <Avatar src={person.avatarUrl} name={person.name} class="size-6" />
                                <span class="max-w-40 truncate">{person.name}</span>
                            </Chip>
                        </li>
                    {/each}
                </ul>
            {:else}
                <p class="text-sm text-gray-400">Tick people on the leaderboard, or search for them here.</p>
            {/if}
        </div>
        <div class="flex flex-col gap-2">
            <h3 class="text-sm font-medium">Amount</h3>
            {@render amountField(
                bulkMode,
                (mode) => (bulkMode = mode),
                bulkAmount,
                (value) => (bulkAmount = value),
            )}
        </div>
        <Button variant="primary" loading={bulkBusy} disabled={!picked.length || !validAmount(bulkAmount, bulkMode)} onclick={applyBulk}>
            {bulkBusy ? "Saving…" : picked.length ? `Apply to ${people(picked.length)}` : "Apply"}
        </Button>
    </div>
{/snippet}

{#snippet profilePanel()}
    {#if profileQuery?.error}
        <EmptyState
            tone="danger"
            compact
            title="Couldn't load this person"
            text={profileQuery.error.message ?? "Square didn't answer. Try again in a moment."}
            retry={() => profileQuery.refresh()}
        />
    {:else if !profile}
        <div aria-label="Loading this person" aria-busy="true" class="flex flex-col gap-6">
            <div class="flex items-center gap-4">
                <span class="size-14 shrink-0 skeleton rounded-full"></span>
                <span class="flex flex-col gap-2">
                    <span class="h-4 w-32 skeleton rounded-full"></span>
                    <span class="h-3 w-40 skeleton rounded-full"></span>
                </span>
            </div>
            <div class="grid grid-cols-3 gap-2">
                {#each [0, 1, 2, 3, 4, 5] as i (i)}
                    <div class="flex min-h-12 flex-col justify-center gap-2 rounded-2xl bg-gray-800 p-4">
                        <span class="h-3 w-12 skeleton rounded-full"></span>
                        <span class="h-5 w-10 skeleton rounded-full"></span>
                    </div>
                {/each}
            </div>
            <div class="flex flex-col gap-2">
                <span class="h-4 w-28 skeleton rounded-full"></span>
                <span class="h-12 skeleton rounded-full md:h-10"></span>
                <span class="h-12 skeleton rounded-full md:h-10"></span>
            </div>
            <div class="flex flex-col gap-2">
                <span class="h-4 w-24 skeleton rounded-full"></span>
                {#each [0, 1, 2] as i (i)}
                    <div class="flex min-h-12 items-center gap-4 rounded-2xl bg-gray-800 p-2">
                        <span class="size-8 shrink-0 skeleton rounded-full"></span>
                        <span class="flex flex-1 flex-col gap-1.5">
                            <span class="h-3.5 w-28 skeleton rounded-full"></span>
                            <span class="h-3 w-16 skeleton rounded-full"></span>
                        </span>
                    </div>
                {/each}
            </div>
        </div>
    {:else}
        <div class="flex flex-col gap-6">
            <div class="flex items-center gap-4">
                <Avatar src={profile.user.avatarUrl} name={profile.user.name} class="size-14" />
                <div class="flex min-w-0 flex-col gap-1">
                    <span class="flex min-w-0 items-center gap-2">
                        <span class="truncate font-medium">{profile.user.name}</span>
                        {#if !profile.member}<Chip tone="muted" size="sm">Not in server</Chip>{/if}
                    </span>
                    <span class="truncate font-mono text-xs text-gray-400">{profile.user.id}</span>
                </div>
            </div>

            <div class="grid grid-cols-3 gap-2">
                <Fact size="lg" label="Invites" value={formatCount(profile.total)} accent />
                <Fact size="lg" label="Rank" value={profile.rank ? `#${formatCount(profile.rank)}` : "None"} />
                <Fact size="lg" label="Bonus" value={formatCount(profile.bonus)} />
                <Fact size="lg" label="Regular" value={formatCount(profile.regular)} />
                <Fact size="lg" label="Left" value={formatCount(profile.left)} />
                <Fact size="lg" label="Fake" value={formatCount(profile.fake)} />
            </div>

            <div class="flex flex-col gap-2">
                <h3 class="text-sm font-medium">Bonus invites</h3>
                {@render amountField(
                    panelMode,
                    (mode) => (panelMode = mode),
                    panelAmount,
                    (value) => (panelAmount = value),
                )}
                <Button variant="primary" loading={panelBusy} disabled={!validAmount(panelAmount, panelMode)} onclick={applyPanelBonus}>
                    {panelBusy ? "Saving…" : panelMode === "add" ? "Add bonus" : "Set bonus"}
                </Button>
            </div>

            <div class="flex flex-col gap-2">
                <h3 class="text-sm font-medium">Invited by</h3>
                {#if profile.invitedBy}
                    <PersonRow person={profile.invitedBy} />
                {:else}
                    <p class="text-sm text-gray-400">Square doesn't know who invited them.</p>
                {/if}
            </div>

            <div class="flex flex-col gap-2">
                <h3 class="text-sm font-medium">Recent invites</h3>
                {#each profile.invitees as invitee (invitee.user.id)}
                    <PersonRow person={invitee.user} detail={day.format(invitee.joinedAt)}>
                        {#if invitee.fake}<Chip tone="warning" size="sm">Fake</Chip>{/if}
                        {#if invitee.left}<Chip tone="muted" size="sm">Left</Chip>{/if}
                    </PersonRow>
                {:else}
                    <p class="text-sm text-gray-400">Nobody joined through their invites yet.</p>
                {/each}
            </div>
        </div>
    {/if}
{/snippet}

<QueryGate queries={[savedQuery]} title="Invites" description="Who invited whom in {data.guild.name}, and how Square counts it.">
    {#snippet skeleton()}<PageSkeleton tabs table="search" />{/snippet}
    <div class="flex flex-col gap-6">
        <PageHeading title="Invites" description="Who invited whom in {data.guild.name}, and how Square counts it." />

        <Tabs
            label="Invites"
            tabs={[
                { value: "leaderboard", label: "Leaderboard", icon: MaterialSymbolsLeaderboardRounded, count: board?.people },
                { value: "settings", label: "Settings", icon: MaterialSymbolsTuneRounded },
            ]}
            bind:value={
                () => tab,
                (next) => {
                    tab = next;
                    details.close();
                }
            }
        >
            {#if tab === "leaderboard"}
                <div class="flex flex-col gap-4">
                    <div class="flex flex-wrap items-center justify-end gap-2">
                        {#if picked.length}
                            <div class="mr-auto flex items-center gap-2 whitespace-nowrap">
                                <span class="text-sm font-medium">{formatCount(picked.length)} picked</span>
                                <Button variant="ghost" onclick={() => (picked = [])}><MaterialSymbolsCloseRounded />Clear</Button>
                            </div>
                        {/if}
                        <UserPicker
                            {guild}
                            title="Find a person"
                            placeholder="Find a person"
                            humansOnly
                            onpick={(user) => open(user)}
                            class="w-full sm:w-64"
                        />
                        <Button variant="primary" onclick={openBulk}>
                            <MaterialSymbolsAddCircleRounded />{picked.length ? `Bonus for ${formatCount(picked.length)}` : "Give bonus"}
                        </Button>
                    </div>

                    {#if boardQuery.error}
                        <EmptyState
                            tone="danger"
                            card
                            title="Couldn't load the leaderboard"
                            text={boardQuery.error.message ?? "Square didn't answer. Try again in a moment."}
                            retry={() => boardQuery.refresh()}
                        />
                    {:else if !board}
                        <TableSkeleton />
                    {:else if !board.entries.length}
                        <EmptyState
                            card
                            icon={MaterialSymbolsGroupAddRounded}
                            title="No invites yet"
                            text="Nobody has invited anyone yet. Give someone bonus invites to start."
                        />
                    {:else}
                        <DataTable
                            label="Invite leaderboard"
                            data={board.entries}
                            {columns}
                            getRowId={(entry) => entry.user.id}
                            manualSorting
                            bind:sorting={
                                () => sorting,
                                (next) => {
                                    sorting = next;
                                    page = 1;
                                }
                            }
                            selectable
                            bind:rowSelection={() => selection, select}
                            active={profileKey}
                            onrowclick={(entry) => open(entry.user)}
                        />
                        <div class="flex items-center justify-end gap-2 empty:hidden">
                            <Pager page={board.page} pages={board.pages} onpage={(next) => (page = next)} />
                        </div>
                    {/if}
                </div>
            {:else}
                <div class="flex flex-col gap-6">
                    <SettingGroup title="Counting">
                        {#snippet actions()}
                            <ResetButton
                                title="Reset invite settings?"
                                done="Invite settings reset"
                                description="The fake account age goes back to {DEFAULT_FAKE_DAYS} days. Invite counts stay as they are."
                                disabled={saved.fakeDays === DEFAULT_FAKE_DAYS}
                                reset={() => settings.resetInvites(guild)}
                                apply={(next) => savedQuery.set(next)}
                            />
                        {/snippet}
                        <SettingRow
                            label="Fake accounts"
                            description="Joins from accounts younger than this many days don't count. 0 counts every account."
                            icon={MaterialSymbolsNoAccountsRounded}
                        >
                            <Input
                                type="number"
                                min={0}
                                max={MAX_FAKE_DAYS}
                                step={1}
                                aria-label="Fake account age in days"
                                invalid={!validDays}
                                bind:value={fakeDays}
                            />
                        </SettingRow>
                    </SettingGroup>

                    <SettingGroup title="Danger zone">
                        <SettingRow
                            label="Reset invite counts"
                            description="Everyone's invites and bonus invites go back to 0, so the leaderboard starts over."
                            icon={MaterialSymbolsLeaderboardRounded}
                            layout="inline"
                        >
                            <ResetButton
                                title="Reset everyone's invites?"
                                done="Invite counts reset"
                                description="Every member's invites and bonus invites go back to 0. This can't be undone."
                                label="Reset counts"
                                reset={() => settings.resetInviteCounts(guild)}
                                apply={(next) => {
                                    savedQuery.set(next);
                                    boardQuery.refresh();
                                }}
                            />
                        </SettingRow>
                    </SettingGroup>
                </div>
            {/if}
        </Tabs>
    </div>

    <SaveBar
        dirty={Object.keys(changes).length > 0}
        invalid={validDays ? "" : `Pick 0 to ${MAX_FAKE_DAYS} days for fake accounts.`}
        onsave={() => settings.updateInvites({ guild, ...changes })}
        ondiscard={() => (fakeDays = saved.fakeDays)}
    />
</QueryGate>
