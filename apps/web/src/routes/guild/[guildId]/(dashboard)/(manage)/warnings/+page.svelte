<script lang="ts">
    import { visible } from "#lib/attachments/visible.ts";
    import ConfirmDialog from "#lib/components/dashboard/ConfirmDialog.svelte";
    import { getDetails } from "#lib/components/dashboard/details.svelte.ts";
    import PageHeading from "#lib/components/dashboard/PageHeading.svelte";
    import PageSkeleton from "#lib/components/dashboard/PageSkeleton.svelte";
    import QueryGate from "#lib/components/dashboard/QueryGate.svelte";
    import SettingGroup from "#lib/components/dashboard/SettingGroup.svelte";
    import SettingRow from "#lib/components/dashboard/SettingRow.svelte";
    import TableSkeleton from "#lib/components/dashboard/TableSkeleton.svelte";
    import Mention from "#lib/components/discord/Mention.svelte";
    import UserPicker from "#lib/components/fields/UserPicker.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import Fact from "#lib/components/ui/Fact.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Pager from "#lib/components/ui/Pager.svelte";
    import PersonRow from "#lib/components/ui/PersonRow.svelte";
    import DataTable from "#lib/components/ui/table/DataTable.svelte";
    import type { TableColumn } from "#lib/components/ui/table/features.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { now } from "#lib/discord/now.svelte.ts";
    import { errorMessage } from "#lib/errors.ts";
    import { dateTime, formatCount, plural, relative } from "#lib/format.ts";
    import { refetch } from "#lib/refetch.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { afterNavigate } from "$app/navigation";
    import type { Person, UserMatch, WarnEntry, WarningItem } from "@square/api-client";
    import { renderSnippet } from "@tanstack/svelte-table";
    import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
    import MaterialSymbolsHardwareRounded from "~icons/material-symbols/hardware-rounded";
    import MaterialSymbolsVerifiedUserRounded from "~icons/material-symbols/verified-user-rounded";
    import MaterialSymbolsWarningRounded from "~icons/material-symbols/warning-rounded";
    import { automodSettings } from "../automod/automod.remote.ts";
    import { durationLabel } from "../automod/automod.ts";
    import type { PageProps } from "./$types";
    import * as remote from "./warnings.remote.ts";

    let { data }: PageProps = $props();

    const DESCRIPTION = "Who got warned and why. Warnings given here work the same as in Discord.";
    const MAX_REASON = 500;
    const WARN = "warn";
    const NO_PERMISSION = "Changing warnings needs the Timeout Members permission";

    const details = getDetails();
    const guild = $derived(data.guild.id);
    const canModerate = $derived(data.guild.canModerate);
    const automodQuery = $derived(automodSettings(guild));
    const steps = $derived([...(automodQuery.current?.punishments ?? [])].sort((a, b) => a.warnings - b.warnings));

    let page = $state(1);
    const rankingQuery = $derived(remote.warningRanking({ guild, page }));
    const ranking = $derived(rankingQuery.current);

    const profileKey = $derived(details.key && details.key !== WARN ? details.key : null);
    const profileQuery = $derived(profileKey ? remote.warningProfile({ guild, user: profileKey, page: 1 }) : null);
    const profile = $derived(profileQuery?.current);

    let more = $state<WarningItem[]>([]);
    let loaded = $state(1);
    let loadingMore = $state(false);
    let moreFailed = $state(false);
    const history = $derived.by(() => {
        const first = profile?.warnings ?? [];
        const seen = new Set(first.map((item) => item.id));
        return [...first, ...more.filter((item) => !seen.has(item.id))];
    });
    const hasMore = $derived(!!profile && loaded < profile.pages);

    $effect(() => {
        void profileKey;
        more = [];
        loaded = 1;
        moreFailed = false;
    });

    async function fetchPage(user: string, page: number) {
        const query = remote.warningProfile({ guild, user, page });
        if (query.ready) await query.refresh();
        return (await query).warnings;
    }

    async function loadMore() {
        if (!profileKey || !hasMore || loadingMore) return;
        const user = profileKey;
        loadingMore = true;
        moreFailed = false;
        try {
            const next = await fetchPage(user, loaded + 1);
            if (user !== profileKey) return;
            more = [...more, ...next];
            loaded += 1;
        } catch {
            moreFailed = true;
        } finally {
            loadingMore = false;
        }
    }

    // Reloads every page already shown, so removing one doesn't throw the list back to the top
    async function reloadHistory() {
        void rankingQuery.refresh();
        if (!profileQuery || !profileKey) return;
        const user = profileKey;
        const shown = loaded;
        await profileQuery.refresh();
        const last = Math.min(shown, profileQuery.current?.pages ?? 1);
        const pages = await Promise.all(Array.from({ length: last - 1 }, (_, index) => fetchPage(user, index + 2)));
        if (user !== profileKey) return;
        more = pages.flat();
        loaded = last;
    }

    afterNavigate(() => {
        refetch(() => rankingQuery);
        refetch(() => profileQuery);
    });

    const ACTIONS = { timeout: "timeout", kick: "kick", ban: "ban" } as const;
    const stepText = (step: (typeof steps)[number]) =>
        `${plural(step.warnings, "warning")}: ${ACTIONS[step.action]}${step.action === "timeout" && step.seconds ? ` for ${durationLabel(step.seconds)}` : ""}`;

    const columns: TableColumn<WarnEntry>[] = [
        { id: "rank", header: "#", enableSorting: false, cell: ({ row }) => renderSnippet(rankCell, row.original), meta: { class: "w-12" } },
        { id: "member", header: "Member", enableSorting: false, cell: ({ row }) => renderSnippet(memberCell, row.original) },
        {
            id: "last",
            header: "Last warned",
            enableSorting: false,
            cell: ({ row }) => renderSnippet(when, row.original.lastAt),
            meta: { class: "hidden w-36 text-gray-400 @2xl:table-cell" },
        },
        {
            id: "warnings",
            header: "Warnings",
            enableSorting: false,
            cell: ({ row }) => renderSnippet(countCell, row.original),
            meta: { align: "end", class: "w-20" },
        },
    ];

    const rankTone = (rank: number) =>
        rank === 1 ? "text-amber-300" : rank === 2 ? "text-gray-200" : rank === 3 ? "text-orange-300" : "text-gray-400";

    function open(person: Pick<Person, "id">) {
        details.show("Warnings", profilePanel, person.id);
        refetch(() => profileQuery);
    }

    let target = $state<Person | null>(null);
    let targetMember = $state(true);
    let reason = $state("");
    let warning = $state(false);

    function openWarn(person: Person | null = null, member = true) {
        target = person;
        targetMember = member;
        reason = "";
        details.show("Warn someone", warnPanel, WARN);
    }

    async function warn() {
        if (!target) return;
        warning = true;
        const person = target;
        try {
            const warned = await remote.giveWarning({ guild, userId: person.id, reason: reason.trim() });
            const notes = [
                `${plural(warned.total, "warning")} now`,
                warned.punishment &&
                    (warned.punished ? warned.punishment : `${warned.punishment} failed, Square's role is too low or it lacks the permission`),
                !warned.messaged && "Their DMs are closed, so they weren't told",
            ].filter(Boolean);
            toast.success(`Warned ${person.name}`, { description: `${notes.join(". ")}.` });
            open(person);
        } catch (err) {
            toast.error(errorMessage(err, "Square couldn't warn them. Try again."));
        } finally {
            warning = false;
        }
    }

    let removing = $state<WarningItem | null>(null);
    let clearing = $state(false);
</script>

{#snippet when(at: number)}
    <Tooltip lazy content={dateTime.format(at)}><time datetime={new Date(at).toISOString()}>{relative(at, now.current)}</time></Tooltip>
{/snippet}

{#snippet rankCell(entry: WarnEntry)}
    <span class={["font-mono font-semibold", rankTone(entry.rank)]}>{formatCount(entry.rank)}</span>
{/snippet}

{#snippet memberCell(entry: WarnEntry)}
    <span class="flex min-w-0 items-center gap-4">
        <Avatar src={entry.user.avatarUrl} name={entry.user.name} class="size-8" />
        <span class="flex min-w-0 flex-col">
            <span class="truncate font-medium">{entry.user.name}</span>
            <span class="truncate text-xs text-gray-400 @2xl:hidden">Warned {@render when(entry.lastAt)}</span>
        </span>
    </span>
{/snippet}

{#snippet countCell(entry: WarnEntry)}
    <span class="font-display text-lg font-semibold">{formatCount(entry.warnings)}</span>
{/snippet}

{#snippet warnPanel()}
    <div class="flex flex-col gap-6">
        <div class="flex flex-col gap-2">
            <h3 class="text-sm font-medium">Member</h3>
            {#if target}
                <PersonRow person={target}>
                    {#if !targetMember}<Chip tone="muted" size="sm">Not in server</Chip>{/if}
                    <Button variant="ghost" disabled={warning} onclick={() => ((target = null), (targetMember = true))}>Change</Button>
                </PersonRow>
            {:else}
                <UserPicker
                    {guild}
                    title="Pick a member"
                    placeholder="Pick a member"
                    humansOnly
                    onpick={(user: UserMatch) => ((target = user), (targetMember = user.member))}
                />
            {/if}
        </div>
        <div class="flex flex-col gap-2">
            <h3 class="text-sm font-medium">Reason</h3>
            <Input
                maxlength={MAX_REASON}
                placeholder="No reason given"
                aria-label="Reason"
                disabled={warning}
                error={reason.length > MAX_REASON ? `Up to ${MAX_REASON} characters` : null}
                bind:value={reason}
            />
        </div>
        <p class="text-sm text-gray-400">
            Square DMs them, posts it in the Moderation log and runs your punishment steps, the same as <Mention kind="command" name="warn" />.
        </p>
        <Tooltip content={!canModerate ? NO_PERMISSION : targetMember ? null : "They're not in the server"}>
            <Button variant="primary" loading={warning} disabled={!target || !targetMember || !canModerate} onclick={warn}>
                {warning ? "Warning…" : target ? `Warn ${target.name}` : "Warn"}
            </Button>
        </Tooltip>
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
                <span class="size-14 shrink-0 skeleton rounded-icon"></span>
                <span class="flex flex-col gap-2">
                    <span class="h-4 w-32 skeleton rounded-md"></span>
                    <span class="h-3 w-40 skeleton rounded-md"></span>
                </span>
            </div>
            <div class="grid grid-cols-2 gap-2">
                {#each [0, 1] as i (i)}
                    <div class="flex min-h-12 flex-col justify-center gap-2 rounded-2xl bg-gray-800 p-4">
                        <span class="h-3 w-12 skeleton rounded-md"></span>
                        <span class="h-5 w-10 skeleton rounded-md"></span>
                    </div>
                {/each}
            </div>
            {#each [0, 1, 2] as i (i)}
                <div class="flex flex-col gap-2 rounded-2xl bg-gray-800 p-4">
                    <span class="h-3.5 w-40 skeleton rounded-md"></span>
                    <span class="h-3 w-56 skeleton rounded-md"></span>
                </div>
            {/each}
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

            <div class="grid grid-cols-2 gap-2">
                <Fact size="lg" label="Warnings" value={formatCount(profile.total)} accent />
                <Fact size="lg" label="Rank" value={profile.rank ? `#${formatCount(profile.rank)}` : "None"} />
            </div>

            <div class="flex flex-wrap gap-2">
                <Tooltip content={!canModerate ? NO_PERMISSION : profile.member ? null : "They're not in the server"}>
                    <Button variant="primary" disabled={!canModerate || !profile.member} onclick={() => openWarn(profile.user)}>
                        <MaterialSymbolsWarningRounded />Warn
                    </Button>
                </Tooltip>
                <Tooltip content={canModerate ? null : NO_PERMISSION}>
                    <Button variant="danger" disabled={!canModerate || !profile.total} onclick={() => (clearing = true)}>
                        <MaterialSymbolsDeleteRounded />Clear all
                    </Button>
                </Tooltip>
            </div>

            <div class="flex flex-col gap-2">
                <h3 class="text-sm font-medium">History</h3>
                {#each history as item (item.id)}
                    <div class="flex items-start gap-2 rounded-2xl bg-gray-800 py-2 pr-2 pl-4">
                        <div class="flex min-w-0 flex-1 flex-col gap-1 py-1">
                            <span class="flex min-w-0 items-center gap-2 text-xs text-gray-400">
                                <span class="font-mono font-semibold text-gray-100">#{formatCount(item.number)}</span>
                                <span aria-hidden="true">·</span>
                                <span class="shrink-0">{@render when(item.createdAt)}</span>
                                <span aria-hidden="true">·</span>
                                {#if item.moderator}
                                    <Tooltip lazy content="Warned by {item.moderator.name}" class="min-w-0">
                                        <span class="flex min-w-0 items-center gap-1">
                                            <Avatar src={item.moderator.avatarUrl} name={item.moderator.name} class="size-4 text-[0.5rem]" />
                                            <span class="truncate">{item.moderator.name}</span>
                                        </span>
                                    </Tooltip>
                                {:else}
                                    <Tooltip lazy content="Given by an AutoMod rule"><span>AutoMod</span></Tooltip>
                                {/if}
                            </span>
                            <p class={["text-sm wrap-break-word", !item.reason && "text-gray-400"]}>{item.reason || "No reason given"}</p>
                        </div>
                        <Tooltip content={canModerate ? "Remove this warning" : NO_PERMISSION}>
                            <Button
                                variant="ghost"
                                icon
                                aria-label="Remove warning #{item.number}"
                                disabled={!canModerate}
                                onclick={() => (removing = item)}
                            >
                                <MaterialSymbolsDeleteRounded />
                            </Button>
                        </Tooltip>
                    </div>
                {:else}
                    <p class="text-sm text-gray-400">{profile.user.name} has no warnings.</p>
                {/each}
                {#if hasMore}
                    {#key loaded}
                        <div {@attach visible(loadMore)} class="flex justify-center">
                            {#if moreFailed}
                                <Button variant="ghost" onclick={loadMore}>Couldn't load more. Try again</Button>
                            {:else}
                                <div
                                    aria-label="Loading more warnings"
                                    aria-busy="true"
                                    class="flex w-full flex-col gap-2 rounded-2xl bg-gray-800 p-4"
                                >
                                    <span class="h-3.5 w-40 skeleton rounded-md"></span>
                                    <span class="h-3 w-56 skeleton rounded-md"></span>
                                </div>
                            {/if}
                        </div>
                    {/key}
                {/if}
            </div>
        </div>

        <ConfirmDialog
            bind:open={() => removing !== null, (next) => !next && (removing = null)}
            title="Remove warning #{removing?.number ?? ''}?"
            description="It no longer counts toward {profile.user.name}'s punishment steps. Punishments it already set off stay."
            label="Remove"
            busy="Removing…"
            done="Warning removed"
            run={() => remote.removeWarning({ guild, user: profile.user.id, warning: removing!.id })}
            apply={reloadHistory}
        />
        <ConfirmDialog
            bind:open={clearing}
            title="Clear every warning?"
            description="All {plural(profile.total, 'warning')} {profile.user.name} has are removed. Punishments they already set off stay."
            label="Clear all"
            busy="Clearing…"
            done="Warnings cleared"
            run={() => remote.clearWarnings({ guild, user: profile.user.id })}
            apply={reloadHistory}
        />
    {/if}
{/snippet}

<QueryGate queries={[automodQuery]} title="Warnings" description={DESCRIPTION}>
    {#snippet skeleton()}<PageSkeleton table="search" />{/snippet}
    <div class="flex flex-col gap-6">
        <PageHeading title="Warnings" description={DESCRIPTION} />

        <SettingGroup>
            <SettingRow
                label={steps.length ? "Punishment steps" : "No punishment steps yet"}
                description={steps.length
                    ? `${steps.map(stepText).join(" · ")}. AutoMod rules set to warn add warnings too.`
                    : "Warnings only count for now. Set what happens at a count, like a timeout at 3 warnings, on the AutoMod page."}
                icon={MaterialSymbolsHardwareRounded}
            >
                <div class="flex @2xl:justify-end">
                    <Button href="/guild/{guild}/automod?tab=warnings">{steps.length ? "Edit steps" : "Set up steps"}</Button>
                </div>
            </SettingRow>
        </SettingGroup>

        <div class="flex flex-col gap-4">
            <div class="flex flex-wrap items-center justify-end gap-2">
                <UserPicker
                    {guild}
                    title="Find a person"
                    placeholder="Find a person"
                    humansOnly
                    onpick={(user) => open(user)}
                    class="min-w-40 flex-1 sm:max-w-64"
                />
                <Tooltip content={canModerate ? null : NO_PERMISSION}>
                    <Button variant="primary" disabled={!canModerate} onclick={() => openWarn()}>
                        <MaterialSymbolsWarningRounded />Warn someone
                    </Button>
                </Tooltip>
            </div>

            {#if rankingQuery.error}
                <EmptyState
                    tone="danger"
                    card
                    title="Couldn't load the warnings"
                    text={rankingQuery.error.message ?? "Square didn't answer. Try again in a moment."}
                    retry={() => rankingQuery.refresh()}
                />
            {:else if !ranking}
                <TableSkeleton />
            {:else if !ranking.entries.length}
                <EmptyState card icon={MaterialSymbolsVerifiedUserRounded} title="No warnings yet">
                    Nobody in {data.guild.name} has been warned. Warn someone here or with <Mention kind="command" name="warn" /> in Discord.
                </EmptyState>
            {:else}
                <DataTable
                    label="Warnings ranking"
                    data={ranking.entries}
                    {columns}
                    getRowId={(entry) => entry.user.id}
                    active={profileKey}
                    onrowclick={(entry) => open(entry.user)}
                />
                <div class="flex flex-wrap items-center justify-end gap-2">
                    <span class="mr-auto text-sm text-gray-400">
                        {plural(ranking.warnings, "warning")} across {ranking.people === 1 ? "1 person" : `${formatCount(ranking.people)} people`}
                    </span>
                    <Pager
                        page={ranking.page}
                        pages={ranking.pages}
                        onpage={(next) => {
                            page = next;
                            refetch(() => rankingQuery);
                        }}
                    />
                </div>
            {/if}
        </div>
    </div>
</QueryGate>
