<script lang="ts">
    import PageHeading from "#lib/components/dashboard/PageHeading.svelte";
    import PageSkeleton from "#lib/components/dashboard/PageSkeleton.svelte";
    import QueryGate from "#lib/components/dashboard/QueryGate.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { errorMessage } from "#lib/errors.ts";
    import { SquarePermissions } from "#lib/permissions.ts";
    import * as settings from "#lib/settings/settings.remote.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { goto } from "$app/navigation";
    import MaterialSymbolsCalendarMonthRounded from "~icons/material-symbols/calendar-month-rounded";
    import MaterialSymbolsRocketLaunchRounded from "~icons/material-symbols/rocket-launch-rounded";
    import { blankDraft, createBody, problemsOf } from "../giveaway.ts";
    import GiveawayEditor from "../GiveawayEditor.svelte";
    import * as giveaways from "../giveaways.remote.ts";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    const guild = $derived(data.guild.id);
    const channelsQuery = $derived(settings.guildChannels(guild));
    const rolesQuery = $derived(settings.guildRoles(guild));
    const permsQuery = $derived(settings.botPermissions(guild));
    const perms = $derived(new SquarePermissions(permsQuery.current));
    const you = $derived({ id: data.user!.id, name: data.user!.name, avatarUrl: data.user!.avatarUrl ?? "" });

    let draft = $state(blankDraft());
    let attempted = $state(false);
    let busy = $state(false);

    const problems = $derived(problemsOf(draft, "new", Date.now()));
    const firstProblem = $derived(Object.values(problems)[0] ?? null);

    async function submit() {
        attempted = true;
        if (firstProblem) {
            toast.error(firstProblem);
            return;
        }
        busy = true;
        try {
            const created = await giveaways.createGiveaway({ guild, ...createBody(draft) });
            toast.success(created.status === "scheduled" ? "Giveaway scheduled" : "Giveaway started");
            await goto(`/guild/${guild}/giveaways/${created.id}`, { replaceState: true });
        } catch (err) {
            toast.error(errorMessage(err, "Square couldn't start the giveaway. Try again."));
        } finally {
            busy = false;
        }
    }
</script>

<QueryGate queries={[channelsQuery, rolesQuery, permsQuery]} title="New giveaway" description="Set it up, see it as it will look, then start it.">
    {#snippet skeleton()}<PageSkeleton
            groups={[
                { rows: 4, title: true },
                { rows: 3, title: true },
            ]}
        />{/snippet}
    <div class="flex flex-col gap-6">
        <PageHeading title="New giveaway" description="Set it up, see it as it will look, then start it.">
            {#snippet actions()}
                <Button variant="ghost" href="/guild/{guild}/giveaways">Cancel</Button>
                <Tooltip content={attempted ? firstProblem : null}>
                    <Button variant="primary" loading={busy} onclick={submit}>
                        {#if !busy}
                            {#if draft.startNow}<MaterialSymbolsRocketLaunchRounded />{:else}<MaterialSymbolsCalendarMonthRounded />{/if}
                        {/if}
                        {busy ? (draft.startNow ? "Starting…" : "Scheduling…") : draft.startNow ? "Start giveaway" : "Schedule giveaway"}
                    </Button>
                </Tooltip>
            {/snippet}
        </PageHeading>

        <GiveawayEditor
            bind:draft
            status="new"
            guild={data.guild}
            {you}
            channels={channelsQuery.current ?? []}
            roles={rolesQuery.current ?? []}
            {perms}
            {problems}
            {attempted}
        />
    </div>
</QueryGate>
