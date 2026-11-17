<script lang="ts">
    import { ripple } from "#lib/attachments/ripple.ts";
    import { getDetails } from "#lib/components/dashboard/details.svelte.ts";
    import PageHeading from "#lib/components/dashboard/PageHeading.svelte";
    import PageSkeleton from "#lib/components/dashboard/PageSkeleton.svelte";
    import QueryGate from "#lib/components/dashboard/QueryGate.svelte";
    import ResetButton from "#lib/components/dashboard/ResetButton.svelte";
    import SaveBar from "#lib/components/dashboard/SaveBar.svelte";
    import SettingGroup from "#lib/components/dashboard/SettingGroup.svelte";
    import SettingRow from "#lib/components/dashboard/SettingRow.svelte";
    import UserPicker from "#lib/components/fields/UserPicker.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import Toggle from "#lib/components/ui/Toggle.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { roleOptions } from "#lib/settings/options.ts";
    import * as settings from "#lib/settings/settings.remote.ts";
    import type { AutoroleUser, UserMatch } from "@square/api-client";
    import MaterialSymbolsCallSplitRounded from "~icons/material-symbols/call-split-rounded";
    import MaterialSymbolsChevronRightRounded from "~icons/material-symbols/chevron-right-rounded";
    import MaterialSymbolsGroupRounded from "~icons/material-symbols/group-rounded";
    import MaterialSymbolsPersonRemoveRounded from "~icons/material-symbols/person-remove-rounded";
    import MaterialSymbolsPersonRounded from "~icons/material-symbols/person-rounded";
    import MaterialSymbolsSmartToyRounded from "~icons/material-symbols/smart-toy-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    const MAX_ROLES = 10;
    const MAX_USERS = 50;

    const details = getDetails();
    const guild = $derived(data.guild.id);
    const savedQuery = $derived(settings.generalSettings(guild));
    const rolesQuery = $derived(settings.guildRoles(guild));

    const saved = $derived(savedQuery.current!);
    const roles = $derived(rolesQuery.current!);

    let humans = $derived(saved.autoroleIds);
    let bots = $derived(saved.autoroleBotIds);
    let split = $derived(saved.autoroleSplit);
    let users = $derived<AutoroleUser[]>(saved.autoroleUsers);

    const sameRoles = (a: string[], b: string[]) => a.length === b.length && a.every((id) => b.includes(id));
    const sameUsers = (a: AutoroleUser[], b: AutoroleUser[]) =>
        a.length === b.length && a.every((entry) => b.some((other) => other.user.id === entry.user.id && sameRoles(other.roleIds, entry.roleIds)));

    const changes = $derived({
        ...(!sameRoles(humans, saved.autoroleIds) && { autoroleIds: humans }),
        ...(!sameRoles(bots, saved.autoroleBotIds) && { autoroleBotIds: bots }),
        ...(split !== saved.autoroleSplit && { autoroleSplit: split }),
        ...(!sameUsers(users, saved.autoroleUsers) && {
            autoroleUsers: users.map((entry) => ({ userId: entry.user.id, roleIds: entry.roleIds })),
        }),
    });
    const invalid = $derived(users.some((entry) => !entry.roleIds.length) ? "Pick at least one role for everyone on the list." : "");

    function discard() {
        humans = saved.autoroleIds;
        bots = saved.autoroleBotIds;
        split = saved.autoroleSplit;
        users = saved.autoroleUsers;
    }

    const roleName = $derived(new Map(roles.map((role) => [role.id, role.name])));
    const keep = $derived([...saved.autoroleIds, ...saved.autoroleBotIds, ...saved.autoroleUsers.flatMap((entry) => entry.roleIds)]);
    const roleChoices = $derived(roleOptions(roles, { assignable: true, keep }));

    const isDefault = $derived(!saved.autoroleIds.length && !saved.autoroleBotIds.length && !saved.autoroleSplit && !saved.autoroleUsers.length);

    const open = (entry: AutoroleUser) => details.show("Extra roles", personPanel, entry.user.id);

    function add(user: UserMatch) {
        const entry = { user: { id: user.id, name: user.name, avatarUrl: user.avatarUrl }, member: user.member, roleIds: [] };
        users = [...users, entry];
        open(entry);
    }

    const setUserRoles = (id: string, roleIds: string[]) => (users = users.map((entry) => (entry.user.id === id ? { ...entry, roleIds } : entry)));
    const remove = (id: string) => (users = users.filter((entry) => entry.user.id !== id));

    $effect(() => {
        if (details.key && !users.some((entry) => entry.user.id === details.key)) details.close();
    });
</script>

{#snippet personPanel()}
    {@const entry = users.find((entry) => entry.user.id === details.key)}
    {#if entry}
        <div class="flex flex-col gap-6">
            <div class="flex items-center gap-4">
                <Avatar src={entry.user.avatarUrl} name={entry.user.name} class="size-14" />
                <div class="flex min-w-0 flex-col">
                    <span class="flex min-w-0 items-center gap-2">
                        <span class="truncate font-medium">{entry.user.name}</span>
                        {#if !entry.member}<Chip tone="muted" size="sm">Not in server</Chip>{/if}
                    </span>
                    <span class="truncate font-mono text-xs text-gray-400">{entry.user.id}</span>
                </div>
            </div>
            <div class="flex flex-col gap-2">
                <h3 class="text-sm font-medium">Extra roles</h3>
                <p class="text-sm text-gray-400">Square adds these when they join, on top of the join roles.</p>
                <Select
                    title="Roles for {entry.user.name}"
                    placeholder="Add a role"
                    options={roleChoices}
                    multiple
                    max={MAX_ROLES}
                    error={entry.roleIds.length ? null : "Pick at least one role."}
                    bind:values={() => entry.roleIds, (next) => setUserRoles(entry.user.id, next)}
                />
            </div>
            <Button variant="danger" onclick={() => remove(entry.user.id)}><MaterialSymbolsPersonRemoveRounded />Remove from list</Button>
        </div>
    {/if}
{/snippet}

<QueryGate queries={[savedQuery, rolesQuery]} title="General" description="The basics Square handles for {data.guild.name}." actions>
    {#snippet skeleton()}<PageSkeleton groups={[{ rows: 3 }, { rows: 2 }]} />{/snippet}
    <div class="flex flex-col gap-6">
        <PageHeading title="General" description="The basics Square handles for {data.guild.name}.">
            {#snippet actions()}
                <ResetButton
                    title="Reset general settings?"
                    done="General settings reset"
                    description="This clears every join role. Nobody loses a role they already have."
                    disabled={isDefault}
                    reset={() => settings.resetGeneral(guild)}
                    apply={(next) => savedQuery.set(next)}
                />
            {/snippet}
        </PageHeading>

        <SettingGroup title="Join roles" description="Square gives these out the moment someone joins.">
            <SettingRow
                label="Separate roles for bots"
                description="Give bots a different set than members."
                icon={MaterialSymbolsCallSplitRounded}
                layout="inline"
            >
                <Toggle label="Separate roles for bots" bind:checked={split} />
            </SettingRow>
            {#if split}
                <SettingRow label="Members" description="People who join." icon={MaterialSymbolsPersonRounded}>
                    <Select title="Member roles" placeholder="Add a role" options={roleChoices} multiple max={MAX_ROLES} bind:values={humans} />
                </SettingRow>
                <SettingRow label="Bots" description="Bots someone adds." icon={MaterialSymbolsSmartToyRounded}>
                    <Select title="Bot roles" placeholder="Add a role" options={roleChoices} multiple max={MAX_ROLES} bind:values={bots} />
                </SettingRow>
            {:else}
                <SettingRow label="Everyone" description="Members and bots alike." icon={MaterialSymbolsGroupRounded}>
                    <Select title="Join roles" placeholder="Add a role" options={roleChoices} multiple max={MAX_ROLES} bind:values={humans} />
                </SettingRow>
            {/if}
        </SettingGroup>

        <SettingGroup title="Extra roles for people" description="On top of the join roles. Works for people who haven't joined yet.">
            {#snippet actions()}
                <Tooltip content={users.length >= MAX_USERS ? `You can add up to ${MAX_USERS} people` : null} class="w-full sm:w-64">
                    <UserPicker
                        {guild}
                        title="Add a person"
                        exclude={users.map((entry) => entry.user.id)}
                        disabled={users.length >= MAX_USERS}
                        onpick={add}
                        class="w-full"
                    />
                </Tooltip>
            {/snippet}
            {#each users as entry (entry.user.id)}
                <button
                    type="button"
                    aria-current={details.key === entry.user.id || undefined}
                    class="ripple flex items-center gap-4 p-4 text-left first:rounded-t-card last:rounded-b-card hover:bg-white/5 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent aria-[current]:bg-white/5"
                    {@attach ripple}
                    onclick={() => open(entry)}
                >
                    <Avatar src={entry.user.avatarUrl} name={entry.user.name} class="size-10" />
                    <span class="flex min-w-0 flex-1 flex-col">
                        <span class="flex min-w-0 items-center gap-2">
                            <span class="truncate text-sm font-medium">{entry.user.name}</span>
                            {#if !entry.member}<Chip tone="muted" size="sm">Not in server</Chip>{/if}
                        </span>
                        {#if entry.roleIds.length}
                            <span class="truncate text-sm text-gray-400">
                                {entry.roleIds.map((id) => roleName.get(id) ?? "Unknown role").join(", ")}
                            </span>
                        {:else}
                            <span class="text-sm text-red-400">No roles picked</span>
                        {/if}
                    </span>
                    <MaterialSymbolsChevronRightRounded class="size-5 shrink-0 text-gray-400" />
                </button>
            {:else}
                <p class="p-4 text-sm text-gray-400">No one added yet.</p>
            {/each}
        </SettingGroup>
    </div>

    <SaveBar dirty={Object.keys(changes).length > 0} {invalid} onsave={() => settings.updateGeneral({ guild, ...changes })} ondiscard={discard} />
</QueryGate>
