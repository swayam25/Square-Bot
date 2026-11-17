<script lang="ts">
    import ConfirmDialog from "#lib/components/dashboard/ConfirmDialog.svelte";
    import PageHeading from "#lib/components/dashboard/PageHeading.svelte";
    import PageSkeleton from "#lib/components/dashboard/PageSkeleton.svelte";
    import QueryGate from "#lib/components/dashboard/QueryGate.svelte";
    import ResetButton from "#lib/components/dashboard/ResetButton.svelte";
    import SaveBar from "#lib/components/dashboard/SaveBar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Dialog from "#lib/components/ui/Dialog.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Segmented from "#lib/components/ui/Segmented.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import Tabs from "#lib/components/ui/Tabs.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { errorMessage } from "#lib/errors.ts";
    import { refetch } from "#lib/refetch.ts";
    import * as settings from "#lib/settings/settings.remote.ts";
    import { load, save as store } from "#lib/storage.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { afterNavigate } from "$app/navigation";
    import type { NativeRule, Punishment, SquareRule } from "@square/api-client";
    import { settled, untrack } from "svelte";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
    import MaterialSymbolsHardwareRounded from "~icons/material-symbols/hardware-rounded";
    import MaterialSymbolsScienceRounded from "~icons/material-symbols/science-rounded";
    import MaterialSymbolsShieldRounded from "~icons/material-symbols/shield-rounded";
    import SimpleIconsDiscord from "~icons/simple-icons/discord";
    import type { PageProps } from "./$types";
    import * as remote from "./automod.remote.ts";
    import {
        copy,
        KINDS,
        nativeChanges,
        nativeProblems,
        punishmentProblems,
        sameJson,
        squareProblems,
        TRIGGER_ORDER,
        TRIGGERS,
        type Mode,
        type Trigger,
    } from "./automod.ts";
    import DiscordRuleEditor from "./DiscordRuleEditor.svelte";
    import Punishments from "./Punishments.svelte";
    import SquareRuleGroup from "./SquareRuleGroup.svelte";
    import TestBox from "./TestBox.svelte";

    let { data }: PageProps = $props();

    const DESCRIPTION = "Catch spam, slurs and rule breakers before your mods have to.";
    const MODE_KEY = "automod-mode";

    const guild = $derived(data.guild.id);
    const settingsQuery = $derived(remote.automodSettings(guild));
    const discordQuery = $derived(remote.discordRules(guild));
    const channelsQuery = $derived(settings.guildChannels(guild));
    const rolesQuery = $derived(settings.guildRoles(guild));
    // Discord's rules can change in Discord's own settings at any time
    afterNavigate(() => refetch(() => discordQuery));

    const saved = $derived(settingsQuery.current ?? { rules: [], punishments: [] });
    const native = $derived(discordQuery.current ?? { rules: [], canManage: true, canTimeout: true });
    const channels = $derived(channelsQuery.current ?? []);
    const roles = $derived(rolesQuery.current ?? []);

    let mode = $state<Mode>(load(MODE_KEY) === "advanced" ? "advanced" : "simple");
    let tab = $state<"discord" | "square" | "warnings" | "test">("discord");

    let rules = $state<SquareRule[]>([]);
    let steps = $state<Punishment[]>([]);
    $effect.pre(() => {
        const next = saved;
        untrack(() => {
            rules = copy(next.rules);
            steps = copy(next.punishments);
        });
    });

    // Each Discord rule's draft resets only when that rule changes, so saving one keeps edits on another
    let drafts = $state<Record<string, NativeRule>>({});
    const bases: Record<string, string> = {};
    $effect.pre(() => {
        for (const rule of native.rules) {
            const key = JSON.stringify(rule);
            if (bases[rule.id] === key) continue;
            bases[rule.id] = key;
            untrack(() => (drafts[rule.id] = copy(rule)));
        }
        for (const id of Object.keys(bases)) {
            if (native.rules.some((rule) => rule.id === id)) continue;
            delete bases[id];
            untrack(() => delete drafts[id]);
        }
    });

    const ordered = $derived(
        [...native.rules].sort((a, b) => TRIGGER_ORDER.indexOf(a.trigger) - TRIGGER_ORDER.indexOf(b.trigger) || a.name.localeCompare(b.name)),
    );
    let pickedRule = $state<string | null>(null);
    const current = $derived(ordered.find((rule) => rule.id === pickedRule) ?? ordered[0]);

    const nativeEdits = $derived(
        native.rules.flatMap((rule) => {
            const draft = drafts[rule.id];
            const patch = draft ? nativeChanges(rule, draft) : {};
            return Object.keys(patch).length ? [{ rule, patch, problems: nativeProblems(draft!) }] : [];
        }),
    );
    const changedRules = $derived(
        rules.filter(
            (rule) =>
                !sameJson(
                    rule,
                    saved.rules.find((entry) => entry.kind === rule.kind),
                ),
        ),
    );
    const stepsChanged = $derived(!sameJson(steps, saved.punishments));
    const stepProblems = $derived(punishmentProblems(steps));
    const dirty = $derived(nativeEdits.length > 0 || changedRules.length > 0 || stepsChanged);

    const invalid = $derived.by(() => {
        for (const edit of nativeEdits) {
            const found = edit.problems;
            if (found.actions) return `${edit.rule.name}: ${found.actions.toLowerCase()}`;
            if (Object.keys(found).length) return `Fix the fields marked in red in ${edit.rule.name}`;
        }
        for (const rule of changedRules) {
            const found = squareProblems(rule);
            if (found.actions) return `${KINDS[rule.kind].label}: ${found.actions.toLowerCase()}`;
            if (Object.keys(found).length) return `Fix the fields marked in red in ${KINDS[rule.kind].label}`;
        }
        if (stepsChanged && Object.keys(stepProblems).length) return "Fix the fields marked in red in Punishments";
        return "";
    });

    async function saveAll() {
        for (const { rule, patch } of nativeEdits) {
            const next = await remote.updateDiscordRule({ guild, id: rule.id, changes: patch });
            discordQuery.set({ ...native, rules: native.rules.map((entry) => (entry.id === next.id ? next : entry)) });
        }
        if (changedRules.length || stepsChanged) {
            const next = await remote.updateAutomod({
                guild,
                ...(changedRules.length && { rules: changedRules }),
                ...(stepsChanged && { punishments: steps.map((step) => ({ ...step, seconds: step.action === "timeout" ? step.seconds : null })) }),
            });
            settingsQuery.set(next);
        }
    }

    function discard() {
        for (const rule of native.rules) drafts[rule.id] = copy(rule);
        rules = copy(saved.rules);
        steps = copy(saved.punishments);
    }

    const counts = $derived(
        Object.fromEntries(TRIGGER_ORDER.map((trigger) => [trigger, native.rules.filter((rule) => rule.trigger === trigger).length])),
    );
    const openTriggers = $derived(TRIGGER_ORDER.filter((trigger) => counts[trigger]! < TRIGGERS[trigger].limit));

    let adding = $state(false);
    let creating = $state(false);
    let newTrigger = $state<string | null>(null);
    let newName = $state("");
    let addProblem = $state("");

    function openAdd() {
        newTrigger = openTriggers[0] ?? null;
        newName = newTrigger ? TRIGGERS[newTrigger as Trigger].label : "";
        addProblem = "";
        adding = true;
    }

    async function create() {
        if (!newTrigger || !newName.trim()) return;
        creating = true;
        addProblem = "";
        try {
            const { created, list } = await remote.createDiscordRule({ guild, trigger: newTrigger as Trigger, name: newName.trim() });
            adding = false;
            creating = false;
            await settled();
            discordQuery.set(list);
            pickedRule = created.id;
            toast.success("Rule added, set it up and turn it on");
        } catch (err) {
            addProblem = errorMessage(err, "Square couldn't add that rule. Try again.");
        } finally {
            creating = false;
        }
    }

    let deleting = $state(false);
    const isDefault = $derived(!saved.rules.some((rule) => rule.enabled) && !saved.punishments.length);
</script>

<QueryGate queries={[settingsQuery, discordQuery, channelsQuery, rolesQuery]} title="AutoMod" description={DESCRIPTION} actions>
    {#snippet skeleton()}<PageSkeleton tabs groups={[{ rows: 2 }, { rows: 4 }, { rows: 3 }]} />{/snippet}
    <div class="flex flex-col gap-6">
        <PageHeading title="AutoMod" description={DESCRIPTION}>
            {#snippet actions()}
                <Segmented
                    label="Detail"
                    options={[
                        { value: "simple", label: "Simple" },
                        { value: "advanced", label: "Advanced" },
                    ]}
                    bind:value={() => mode, (next) => store(MODE_KEY, (mode = next))}
                />
                <ResetButton
                    title="Reset Square's rules?"
                    done="Square's rules reset"
                    description="This turns off Square's own rules and removes every punishment step. Discord's rules and members' warnings stay."
                    disabled={isDefault}
                    reset={() => remote.resetAutomod(guild)}
                    apply={(next) => settingsQuery.set(next)}
                />
            {/snippet}
        </PageHeading>

        <Tabs
            label="AutoMod"
            tabs={[
                { value: "discord", label: "Discord rules", icon: SimpleIconsDiscord, count: native.rules.length },
                { value: "square", label: "Square rules", icon: MaterialSymbolsShieldRounded, count: rules.filter((rule) => rule.enabled).length },
                { value: "warnings", label: "Warnings", icon: MaterialSymbolsHardwareRounded },
                { value: "test", label: "Test", icon: MaterialSymbolsScienceRounded },
            ]}
            bind:value={tab}
        >
            {#if tab === "discord"}
                {#if !native.canManage}
                    <EmptyState
                        card
                        icon={SimpleIconsDiscord}
                        title="Square can't see these rules"
                        text="Discord only shares its AutoMod rules with bots that have the Manage Server permission."
                    />
                {:else if !current}
                    <EmptyState
                        card
                        icon={SimpleIconsDiscord}
                        title="No Discord rules yet"
                        text="Discord runs these itself, so they work even while Square is offline."
                    >
                        {#snippet action()}
                            <Button variant="primary" onclick={openAdd}><MaterialSymbolsAddRounded />Add a rule</Button>
                        {/snippet}
                    </EmptyState>
                {:else}
                    <div class="flex flex-col gap-6">
                        <div class="flex flex-wrap items-center gap-2">
                            <Segmented
                                label="Rule"
                                class="w-fit max-w-full min-w-0"
                                options={ordered.map((rule) => ({
                                    value: rule.id,
                                    label: drafts[rule.id]?.name || rule.name,
                                    icon: TRIGGERS[rule.trigger].icon,
                                }))}
                                bind:value={() => current.id, (next) => (pickedRule = next)}
                            />
                            <div class="ml-auto flex gap-2">
                                <Tooltip content="Delete this rule">
                                    <Button variant="ghost-danger" icon onclick={() => (deleting = true)}><MaterialSymbolsDeleteRounded /></Button>
                                </Tooltip>
                                <Tooltip content={openTriggers.length ? null : "Discord's rule limits are all used"}>
                                    <Button disabled={!openTriggers.length} onclick={openAdd}><MaterialSymbolsAddRounded />Add rule</Button>
                                </Tooltip>
                            </div>
                        </div>
                        {#if drafts[current.id]}
                            {#key current.id}
                                <DiscordRuleEditor
                                    bind:rule={drafts[current.id]!}
                                    {mode}
                                    {channels}
                                    {roles}
                                    canTimeout={native.canTimeout}
                                    problems={nativeProblems(drafts[current.id]!)}
                                />
                            {/key}
                        {/if}
                    </div>
                {/if}
            {:else if tab === "square"}
                <div class="flex flex-col gap-4">
                    <p class="px-2 text-sm text-gray-400">
                        Square runs these on top of Discord's. People with Manage Messages, bots and webhooks are never caught.
                    </p>
                    {#each rules as rule, index (rule.kind)}
                        <SquareRuleGroup bind:rule={rules[index]!} {mode} {channels} {roles} problems={squareProblems(rule)} />
                    {/each}
                </div>
            {:else if tab === "warnings"}
                <Punishments bind:steps problems={stepProblems} />
            {:else}
                <TestBox guild={data.guild} {channels} {dirty} />
            {/if}
        </Tabs>
    </div>

    <SaveBar {dirty} {invalid} onsave={saveAll} ondiscard={discard} />
</QueryGate>

<Dialog bind:open={() => adding, (next) => !creating && (adding = next)} title="Add a Discord rule" dismissable={!creating}>
    <div class="flex flex-col gap-4 text-sm">
        <p class="text-gray-400">It starts off, so nothing is caught until you set it up and turn it on.</p>
        <Select
            title="Kind of rule"
            options={openTriggers.map((trigger) => ({
                value: trigger,
                label: TRIGGERS[trigger].label,
                icon: TRIGGERS[trigger].icon,
                hint: `${counts[trigger]} of ${TRIGGERS[trigger].limit}`,
            }))}
            disabled={creating}
            bind:value={
                () => newTrigger,
                (next) => {
                    if (!newTrigger || newName === TRIGGERS[newTrigger as Trigger].label) newName = next ? TRIGGERS[next as Trigger].label : "";
                    newTrigger = next;
                }
            }
        />
        <Input aria-label="Rule name" placeholder="Rule name" maxlength={100} disabled={creating} bind:value={newName} />
        {#if addProblem}<p class="font-medium text-red-400">{addProblem}</p>{/if}
    </div>
    {#snippet footer()}
        <Button variant="ghost" disabled={creating} onclick={() => (adding = false)}>Cancel</Button>
        <Button variant="primary" loading={creating} disabled={!newTrigger || !newName.trim()} onclick={create}
            >{creating ? "Adding…" : "Add rule"}</Button
        >
    {/snippet}
</Dialog>

{#if current}
    <ConfirmDialog
        bind:open={deleting}
        title="Delete {current.name}?"
        description="Discord stops running it right away. This can't be undone."
        label="Delete"
        busy="Deleting…"
        done="Rule deleted"
        run={() => remote.deleteDiscordRule({ guild, id: current.id })}
        apply={(next) => {
            discordQuery.set(next);
            pickedRule = null;
        }}
    />
{/if}
