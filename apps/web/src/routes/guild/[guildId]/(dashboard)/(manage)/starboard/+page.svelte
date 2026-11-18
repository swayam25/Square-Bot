<script lang="ts">
    import ConfirmDialog from "#lib/components/dashboard/ConfirmDialog.svelte";
    import PageHeading from "#lib/components/dashboard/PageHeading.svelte";
    import PageSkeleton from "#lib/components/dashboard/PageSkeleton.svelte";
    import QueryGate from "#lib/components/dashboard/QueryGate.svelte";
    import SaveBar from "#lib/components/dashboard/SaveBar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Dialog from "#lib/components/ui/Dialog.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import Segmented from "#lib/components/ui/Segmented.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { errorMessage } from "#lib/errors.ts";
    import { SquarePermissions } from "#lib/permissions.ts";
    import { refetch } from "#lib/refetch.ts";
    import { usableTextChannels } from "#lib/settings/options.ts";
    import * as settings from "#lib/settings/settings.remote.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { afterNavigate } from "$app/navigation";
    import type { Starboard } from "@square/api-client";
    import { settled, untrack } from "svelte";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
    import MaterialSymbolsStarRounded from "~icons/material-symbols/star-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import type { PageProps } from "./$types";
    import { changes, fromBoard, LIMITS, problems, type Draft } from "./board.ts";
    import BoardEditor from "./BoardEditor.svelte";
    import * as remote from "./starboard.remote.ts";

    let { data }: PageProps = $props();

    const DESCRIPTION = "Messages people vote for with reactions get a spot on a board.";

    const guild = $derived(data.guild.id);
    const you = $derived({ id: data.user!.id, name: data.user!.name, avatarUrl: data.user!.avatarUrl ?? "" });
    const boardsQuery = $derived(remote.starboards(guild));
    const channelsQuery = $derived(settings.guildChannels(guild));
    const rolesQuery = $derived(settings.guildRoles(guild));
    const permsQuery = $derived(settings.botPermissions(guild));
    // Deleting a board's channel turns the board off without the dashboard
    afterNavigate(() => refetch(() => boardsQuery));

    const boards = $derived(boardsQuery.current ?? []);
    const channels = $derived(channelsQuery.current ?? []);
    const perms = $derived(new SquarePermissions(permsQuery.current));
    const channelName = (id: string) => channels.find((channel) => channel.id === id)?.name ?? "deleted-channel";

    // Each board's draft resets only when that board changes on the bot, so saving one keeps edits on another
    let drafts = $state<Record<number, Draft>>({});
    const bases: Record<number, string> = {};
    $effect.pre(() => {
        for (const board of boards) {
            const key = JSON.stringify(board);
            if (bases[board.id] === key) continue;
            bases[board.id] = key;
            untrack(() => (drafts[board.id] = fromBoard(board)));
        }
        for (const id of Object.keys(bases).map(Number)) {
            if (boards.some((board) => board.id === id)) continue;
            delete bases[id];
            untrack(() => delete drafts[id]);
        }
    });

    let picked = $state<number | null>(null);
    const current = $derived(boards.find((board) => board.id === picked) ?? boards[0]);
    const draft = $derived(current ? drafts[current.id] : undefined);

    const edits = $derived(
        boards.flatMap((board) => {
            const next = drafts[board.id];
            const patch = next ? changes(board, next) : {};
            return Object.keys(patch).length ? [{ board, patch, problems: problems(next!) }] : [];
        }),
    );
    const invalid = $derived.by(() => {
        const broken = edits.find((edit) => Object.keys(edit.problems).length);
        if (!broken) return "";
        return boards.length > 1 && broken.board.id !== current?.id ? "Another board has fields marked in red" : "Fix the fields marked in red";
    });

    async function save() {
        const saved: Record<number, Starboard> = {};
        for (const { board, patch } of edits) saved[board.id] = await remote.updateStarboard({ guild, id: board.id, changes: patch });
        boardsQuery.set(boards.map((board) => saved[board.id] ?? board));
    }

    function discard() {
        for (const board of boards) drafts[board.id] = fromBoard(board);
    }

    const taken = $derived(
        current ? boards.filter((board) => board.id !== current.id).map((board) => drafts[board.id]?.channelId ?? board.channelId) : [],
    );

    let adding = $state(false);
    let creating = $state(false);
    let newChannel = $state<string | null>(null);
    const boardChannels = $derived(usableTextChannels(channels, perms, "attach"));
    const freeChannels = $derived(boardChannels.options.filter((option) => !boards.some((board) => board.channelId === option.value)));
    const full = $derived(boards.length >= LIMITS.boards);

    async function create() {
        if (!newChannel) return;
        creating = true;
        try {
            const board = await remote.createStarboard({ guild, channelId: newChannel });
            adding = false;
            creating = false;
            await settled();
            boardsQuery.set([...boards, board]);
            picked = board.id;
            newChannel = null;
            toast.success("Starboard made");
        } catch (err) {
            toast.error(errorMessage(err, "Square couldn't make that starboard. Try again."));
        } finally {
            creating = false;
        }
    }

    let deleting = $state(false);
</script>

<QueryGate queries={[boardsQuery, channelsQuery, rolesQuery, permsQuery]} title="Starboard" description={DESCRIPTION} actions>
    {#snippet skeleton()}<PageSkeleton groups={[{ rows: 2 }, { rows: 4 }, { rows: 4 }]} />{/snippet}
    <div class="flex flex-col gap-6">
        <PageHeading title="Starboard" description={DESCRIPTION}>
            {#snippet actions()}
                {#if current}
                    <Tooltip content="Delete this starboard">
                        <Button variant="ghost-danger" icon onclick={() => (deleting = true)}><MaterialSymbolsDeleteRounded /></Button>
                    </Tooltip>
                {/if}
                {#if boards.length}
                    <Tooltip content={full ? `Up to ${LIMITS.boards} starboards` : null}>
                        <Button disabled={full} onclick={() => (adding = true)}><MaterialSymbolsAddRounded />Add board</Button>
                    </Tooltip>
                {/if}
            {/snippet}
        </PageHeading>

        {#if !current || !draft}
            <EmptyState
                card
                icon={MaterialSymbolsStarRounded}
                title="No starboard yet"
                text="Pick a channel, and messages people star show up there."
            >
                {#snippet action()}
                    <Button variant="primary" onclick={() => (adding = true)}><MaterialSymbolsAddRounded />Make a starboard</Button>
                {/snippet}
            </EmptyState>
        {:else}
            {#if boards.length > 1}
                <Segmented
                    label="Starboard"
                    class="w-fit max-w-full"
                    options={boards.map((board) => ({
                        value: String(board.id),
                        label: channelName(board.channelId),
                        icon: MaterialSymbolsTagRounded,
                    }))}
                    bind:value={() => String(current.id), (next) => (picked = Number(next))}
                />
            {/if}
            {#key current.id}
                <BoardEditor
                    bind:draft={drafts[current.id]!}
                    guild={data.guild}
                    {you}
                    {channels}
                    roles={rolesQuery.current ?? []}
                    {perms}
                    {taken}
                    problems={problems(draft)}
                />
            {/key}
        {/if}
    </div>

    <SaveBar dirty={edits.length > 0} {invalid} onsave={save} ondiscard={discard} />
</QueryGate>

<Dialog bind:open={() => adding, (next) => !creating && (adding = next)} title="Add a starboard" dismissable={!creating}>
    <div class="flex flex-col gap-4 text-sm">
        <p class="text-gray-400">Messages that get enough votes are posted in this channel. Square needs to send messages with files there.</p>
        <Select
            title="Board channel"
            placeholder="Pick a channel"
            options={freeChannels}
            note={boardChannels.note}
            disabled={creating}
            bind:value={newChannel}
        />
    </div>
    {#snippet footer()}
        <Button variant="ghost" disabled={creating} onclick={() => (adding = false)}>Cancel</Button>
        <Button variant="primary" loading={creating} disabled={!newChannel} onclick={create}>{creating ? "Making…" : "Make starboard"}</Button>
    {/snippet}
</Dialog>

{#if current}
    <ConfirmDialog
        bind:open={deleting}
        title="Delete this starboard?"
        description="Votes stop counting here. Posts already on the board stay in the channel."
        label="Delete"
        busy="Deleting…"
        done="Starboard deleted"
        run={() => remote.deleteStarboard({ guild, id: current.id })}
        apply={(next) => {
            boardsQuery.set(next);
            picked = null;
        }}
    />
{/if}
