<script lang="ts">
    import ConfirmDialog from "#lib/components/dashboard/ConfirmDialog.svelte";
    import { getDetails } from "#lib/components/dashboard/details.svelte.ts";
    import PageHeading from "#lib/components/dashboard/PageHeading.svelte";
    import PageSkeleton from "#lib/components/dashboard/PageSkeleton.svelte";
    import QueryGate from "#lib/components/dashboard/QueryGate.svelte";
    import SaveBar from "#lib/components/dashboard/SaveBar.svelte";
    import Mention from "#lib/components/discord/Mention.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import Fact from "#lib/components/ui/Fact.svelte";
    import Tabs from "#lib/components/ui/Tabs.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { now } from "#lib/discord/now.svelte.ts";
    import { errorMessage } from "#lib/errors.ts";
    import { dateTime, formatCount, relative } from "#lib/format.ts";
    import { SquarePermissions } from "#lib/permissions.ts";
    import { refetch } from "#lib/refetch.ts";
    import * as settings from "#lib/settings/settings.remote.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { afterNavigate, goto } from "$app/navigation";
    import { page } from "$app/state";
    import type { Giveaway, Person } from "@square/api-client";
    import { untrack } from "svelte";
    import MaterialSymbolsArrowBackRounded from "~icons/material-symbols/arrow-back-rounded";
    import MaterialSymbolsCasinoRounded from "~icons/material-symbols/casino-rounded";
    import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
    import MaterialSymbolsEditRounded from "~icons/material-symbols/edit-rounded";
    import MaterialSymbolsGroupRounded from "~icons/material-symbols/group-rounded";
    import MaterialSymbolsOpenInNewRounded from "~icons/material-symbols/open-in-new-rounded";
    import MaterialSymbolsRocketLaunchRounded from "~icons/material-symbols/rocket-launch-rounded";
    import MaterialSymbolsStopCircleRounded from "~icons/material-symbols/stop-circle-rounded";
    import { blankDraft, draftOf, patchBody, problemsOf, statusName, statusTone } from "../giveaway.ts";
    import GiveawayEditor from "../GiveawayEditor.svelte";
    import * as giveaways from "../giveaways.remote.ts";
    import type { PageProps } from "./$types";
    import Entrants from "./Entrants.svelte";

    let { data }: PageProps = $props();

    const details = getDetails();
    const guild = $derived(data.guild.id);
    const id = $derived(Number(page.params.id));
    const giveawayQuery = $derived(giveaways.giveaway({ guild, id }));
    const channelsQuery = $derived(settings.guildChannels(guild));
    const rolesQuery = $derived(settings.guildRoles(guild));
    const permsQuery = $derived(settings.botPermissions(guild));
    afterNavigate(() => refetch(() => giveawayQuery));

    const saved = $derived(giveawayQuery.current!);
    const channels = $derived(channelsQuery.current ?? []);
    const perms = $derived(new SquarePermissions(permsQuery.current));
    const channelName = $derived(channels.find((channel) => channel.id === saved?.channelId)?.name ?? "deleted-channel");
    const you = $derived({ id: data.user!.id, name: data.user!.name, avatarUrl: data.user!.avatarUrl ?? "" });

    let tab = $state<"entries" | "edit">("entries");

    let draft = $state(blankDraft());
    let base = "";
    $effect.pre(() => {
        if (!saved) return;
        const next = draftOf(saved);
        const key = JSON.stringify({ ...next, bonusRoles: saved.bonusRoles });
        if (key === base) return;
        base = key;
        untrack(() => (draft = next));
    });
    const problems = $derived(saved ? problemsOf(draft, saved.status, Date.now()) : {});
    const changes = $derived(saved ? patchBody(draft, saved) : {});
    const dirty = $derived(Object.keys(changes).length > 0);

    async function save() {
        const next = await giveaways.updateGiveaway({ guild, id, changes });
        giveawayQuery.set(next);
        toast.success("Giveaway saved");
    }

    let starting = $state(false);
    async function startNow() {
        starting = true;
        try {
            giveawayQuery.set(await giveaways.startGiveaway({ guild, id }));
            toast.success("Giveaway started");
        } catch (err) {
            toast.error(errorMessage(err, "Square couldn't start it. Try again."));
        } finally {
            starting = false;
        }
    }

    type Ask = { title: string; description: string; label: string; busy: string; done: string; run: () => Promise<Giveaway | null> };
    let ask = $state<Ask>({ title: "", description: "", label: "", busy: "", done: "", run: async () => null });
    let asking = $state(false);
    const confirm = (next: Ask) => ((ask = next), (asking = true));

    const endNow = () =>
        confirm({
            title: `End ${saved.prize} now?`,
            description: "Square picks the winners right away and announces them in Discord.",
            label: "End now",
            busy: "Ending…",
            done: "Giveaway ended",
            run: () => giveaways.endGiveaway({ guild, id }),
        });

    const rerollAll = () =>
        confirm({
            title: "Reroll every winner?",
            description: "Square draws new winners from everyone who hasn't won yet and announces them in Discord.",
            label: "Reroll",
            busy: "Rerolling…",
            done: "New winners picked",
            run: () => giveaways.rerollGiveaway({ guild, id, userIds: null }),
        });

    const rerollOne = (person: Person) =>
        confirm({
            title: `Replace ${person.name}?`,
            description: "Square draws someone who hasn't won yet in their place and announces it in Discord.",
            label: "Reroll",
            busy: "Rerolling…",
            done: "New winner picked",
            run: () => giveaways.rerollGiveaway({ guild, id, userIds: [person.id] }),
        });

    const remove = () =>
        confirm({
            title: `Delete ${saved.prize}?`,
            description: "Its message in Discord and every entry go with it. This can't be undone.",
            label: "Delete",
            busy: "Deleting…",
            done: "Giveaway deleted",
            run: async () => {
                await giveaways.deleteGiveaway({ guild, id });
                return null;
            },
        });

    function applied(next: Giveaway | null) {
        if (next) giveawayQuery.set(next);
        else goto(`/guild/${guild}/giveaways`, { replaceState: true });
    }
</script>

<QueryGate queries={[giveawayQuery, channelsQuery, rolesQuery, permsQuery]} title="Giveaway">
    {#snippet skeleton()}<PageSkeleton tabs table="search" />{/snippet}
    <div class="flex flex-col gap-6">
        <Button variant="ghost" size="sm" class="w-fit" href="/guild/{guild}/giveaways"><MaterialSymbolsArrowBackRounded />Giveaways</Button>

        <PageHeading title={saved.prize}>
            {#snippet actions()}
                {#if saved.messageUrl}
                    <Tooltip content="Open in Discord">
                        <Button variant="ghost" icon href={saved.messageUrl} target="_blank" rel="noopener">
                            <MaterialSymbolsOpenInNewRounded />
                        </Button>
                    </Tooltip>
                {/if}
                <Tooltip content="Delete giveaway">
                    <Button variant="ghost-danger" icon onclick={remove}><MaterialSymbolsDeleteRounded /></Button>
                </Tooltip>
                {#if saved.status === "scheduled"}
                    <Button variant="primary" loading={starting} onclick={startNow}>
                        {#if !starting}<MaterialSymbolsRocketLaunchRounded />{/if}{starting ? "Starting…" : "Start now"}
                    </Button>
                {:else if saved.status === "running"}
                    <Button variant="primary" onclick={endNow}><MaterialSymbolsStopCircleRounded />End now</Button>
                {:else}
                    <Tooltip content={saved.entries ? null : "Nobody entered this giveaway"}>
                        <Button variant="primary" disabled={!saved.entries} onclick={rerollAll}><MaterialSymbolsCasinoRounded />Reroll</Button>
                    </Tooltip>
                {/if}
            {/snippet}
        </PageHeading>

        <div class="flex flex-wrap items-center gap-2 text-sm text-gray-400">
            {#if saved.status === "ended" && !saved.posted}
                <Chip tone="danger" size="sm">Not posted</Chip>
            {:else}
                <Chip tone={statusTone[saved.status]} size="sm">{statusName[saved.status]}</Chip>
            {/if}
            <Mention kind="channel" name={channelName} />
            <span class="flex items-center gap-2">
                · Hosted by <Avatar src={saved.host.avatarUrl} name={saved.host.name} class="size-5" /><span class="text-gray-100">
                    {saved.host.name}
                </span>
            </span>
        </div>

        <div class="grid grid-cols-2 gap-2 md:grid-cols-4">
            <Fact size="lg" label="People in" value={formatCount(saved.entries)} accent />
            <Fact size="lg" label="Winners" value={formatCount(saved.winnerCount)} />
            <Fact
                label={saved.status === "scheduled" ? "Starts" : "Started"}
                value={saved.status === "scheduled" ? relative(saved.startsAt, now.current) : dateTime.format(saved.startsAt)}
            />
            <Fact
                label={saved.status === "ended" ? "Ended" : "Ends"}
                value={saved.status === "ended" ? dateTime.format(saved.endedAt ?? saved.endsAt) : relative(saved.endsAt, now.current)}
            />
        </div>

        {#if saved.status === "ended"}
            <section class="flex flex-col gap-2">
                <h2 class="px-2 font-display text-lg font-semibold">{saved.winners.length === 1 ? "Winner" : "Winners"}</h2>
                {#if saved.winners.length}
                    <ul class="grid gap-2 md:grid-cols-2">
                        {#each saved.winners as winner (winner.id)}
                            <li class="flex min-h-14 items-center gap-4 rounded-2xl bg-gray-900 py-2 pr-2 pl-4">
                                <Avatar src={winner.avatarUrl} name={winner.name} class="size-10" />
                                <span class="min-w-0 flex-1 truncate font-medium">{winner.name}</span>
                                <Tooltip content="Reroll {winner.name}">
                                    <Button variant="ghost" icon onclick={() => rerollOne(winner)}><MaterialSymbolsCasinoRounded /></Button>
                                </Tooltip>
                            </li>
                        {/each}
                    </ul>
                {:else}
                    <p class="rounded-2xl bg-gray-900 p-4 text-sm text-gray-400">
                        Nobody could win. Either nobody entered, or nobody who entered still met the requirements.
                    </p>
                {/if}
            </section>
        {/if}

        <Tabs
            label="Giveaway"
            tabs={[
                { value: "entries", label: "Entries", icon: MaterialSymbolsGroupRounded, count: saved.entries || undefined },
                { value: "edit", label: "Edit", icon: MaterialSymbolsEditRounded },
            ]}
            bind:value={
                () => tab,
                (next) => {
                    tab = next;
                    details.close();
                }
            }
        >
            {#if tab === "entries"}
                <Entrants {guild} giveaway={saved} onchange={() => giveawayQuery.refresh()} />
            {:else}
                <div class="flex flex-col gap-6">
                    <GiveawayEditor
                        bind:draft
                        status={saved.status}
                        guild={data.guild}
                        {you}
                        {channels}
                        roles={rolesQuery.current ?? []}
                        {perms}
                        {problems}
                        attempted
                        entries={saved.entries}
                        winners={saved.winners}
                        endedAt={saved.endedAt}
                        storedImage={saved.imageSrc ?? (saved.imageFile ? `/guild/${guild}/giveaways/${id}/image?v=${saved.imageFile}` : null)}
                    />
                    <SaveBar {dirty} invalid={Object.values(problems)[0] ?? ""} onsave={save} ondiscard={() => (draft = draftOf(saved))} />
                </div>
            {/if}
        </Tabs>
    </div>
</QueryGate>

<ConfirmDialog
    bind:open={asking}
    title={ask.title}
    description={ask.description}
    label={ask.label}
    busy={ask.busy}
    done={ask.done}
    run={ask.run}
    apply={applied}
/>
