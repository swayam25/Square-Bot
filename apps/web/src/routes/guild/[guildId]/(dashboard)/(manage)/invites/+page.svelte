<script lang="ts">
    import PageHeading from "#lib/components/PageHeading.svelte";
    import QueryGate from "#lib/components/QueryGate.svelte";
    import ResetButton from "#lib/components/ResetButton.svelte";
    import SaveBar from "#lib/components/SaveBar.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import * as settings from "#lib/settings.remote.ts";
    import MaterialSymbolsLeaderboardRounded from "~icons/material-symbols/leaderboard-rounded";
    import MaterialSymbolsNoAccountsRounded from "~icons/material-symbols/no-accounts-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    const MAX_FAKE_DAYS = 365;
    const DEFAULT_FAKE_DAYS = 7;

    const guild = $derived(data.guild.id);
    const savedQuery = $derived(settings.inviteSettings(guild));
    const saved = $derived(savedQuery.current!);

    let fakeDays = $derived<number | null>(saved.fakeDays);
    const validDays = $derived(Number.isInteger(fakeDays) && fakeDays! >= 0 && fakeDays! <= MAX_FAKE_DAYS);
    const changes = $derived({ ...(fakeDays !== saved.fakeDays && { fakeDays: fakeDays! }) });
</script>

<QueryGate queries={[savedQuery]} title="Invites" description="How Square counts who invited whom in {data.guild.name}.">
    <div class="flex flex-col gap-8">
        <PageHeading title="Invites" description="How Square counts who invited whom in {data.guild.name}." />

        <div class="grid gap-4 lg:grid-cols-2">
            <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
                <div class="flex items-start gap-4">
                    <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-accent">
                        <MaterialSymbolsNoAccountsRounded class="size-6" />
                    </span>
                    <div class="flex min-w-0 flex-1 flex-col gap-1">
                        <h2 class="font-display text-xl font-semibold">Fake accounts</h2>
                        <p class="text-sm text-mist-400">
                            Joins from accounts younger than this count as fake and don't add to anyone's invites. Set 0 to count every account.
                        </p>
                    </div>
                </div>
                <div class="flex flex-col gap-2">
                    <div class="flex gap-2">
                        <Input
                            type="number"
                            min={0}
                            max={MAX_FAKE_DAYS}
                            step={1}
                            aria-label="Fake account age in days"
                            invalid={!validDays}
                            bind:value={fakeDays}
                            class="md:max-w-48"
                        />
                        <ResetButton
                            title="Reset the fake account age?"
                            done="Fake account age reset"
                            description="It goes back to {DEFAULT_FAKE_DAYS} days. Invite counts stay as they are."
                            disabled={saved.fakeDays === DEFAULT_FAKE_DAYS}
                            reset={() => settings.resetInvites(guild)}
                            apply={(next) => savedQuery.set(next)}
                        />
                    </div>
                    <p class={["text-xs", validDays ? "text-mist-400" : "text-red-400"]}>Days, from 0 to {MAX_FAKE_DAYS}.</p>
                </div>
            </section>
            <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
                <div class="flex items-start gap-4">
                    <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-accent">
                        <MaterialSymbolsLeaderboardRounded class="size-6" />
                    </span>
                    <div class="flex min-w-0 flex-1 flex-col gap-1">
                        <h2 class="font-display text-xl font-semibold">Invite counts</h2>
                        <p class="text-sm text-mist-400">Clears everyone's invites and bonus invites, so the leaderboard starts over.</p>
                    </div>
                </div>
                <div>
                    <ResetButton
                        title="Reset everyone's invites?"
                        done="Invite counts reset"
                        description="Every member's invites and bonus invites go back to 0. This can't be undone."
                        label="Reset counts"
                        reset={() => settings.resetInviteCounts(guild)}
                        apply={(next) => savedQuery.set(next)}
                    />
                </div>
            </section>
        </div>
    </div>

    <SaveBar
        dirty={Object.keys(changes).length > 0}
        invalid={validDays ? "" : `Pick 0 to ${MAX_FAKE_DAYS} days for fake accounts.`}
        onsave={() => settings.updateInvites({ guild, ...changes })}
        ondiscard={() => (fakeDays = saved.fakeDays)}
    />
</QueryGate>
