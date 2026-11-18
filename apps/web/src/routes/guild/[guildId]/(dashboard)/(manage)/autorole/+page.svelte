<script lang="ts">
    import { ripple } from "#lib/attachments/ripple.ts";
    import { getDetails } from "#lib/components/dashboard/details.svelte.ts";
    import PageHeading from "#lib/components/dashboard/PageHeading.svelte";
    import PageSkeleton from "#lib/components/dashboard/PageSkeleton.svelte";
    import PermissionNotice from "#lib/components/dashboard/PermissionNotice.svelte";
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
    import { formatCount } from "#lib/format.ts";
    import { SquarePermissions } from "#lib/permissions.ts";
    import { givableRoles, roleOptions } from "#lib/settings/options.ts";
    import * as settings from "#lib/settings/settings.remote.ts";
    import type { AutoroleUser, UserMatch } from "@square/api-client";
    import MaterialSymbolsBlockRounded from "~icons/material-symbols/block-rounded";
    import MaterialSymbolsCallSplitRounded from "~icons/material-symbols/call-split-rounded";
    import MaterialSymbolsChevronRightRounded from "~icons/material-symbols/chevron-right-rounded";
    import MaterialSymbolsGroupRounded from "~icons/material-symbols/group-rounded";
    import MaterialSymbolsHistoryRounded from "~icons/material-symbols/history-rounded";
    import MaterialSymbolsHowToRegRounded from "~icons/material-symbols/how-to-reg-rounded";
    import MaterialSymbolsPersonRemoveRounded from "~icons/material-symbols/person-remove-rounded";
    import MaterialSymbolsPersonRounded from "~icons/material-symbols/person-rounded";
    import MaterialSymbolsScheduleRounded from "~icons/material-symbols/schedule-rounded";
    import MaterialSymbolsSmartToyRounded from "~icons/material-symbols/smart-toy-rounded";
    import type { PageProps } from "./$types";
    import * as remote from "./autorole.remote.ts";

    let { data }: PageProps = $props();

    const MAX_ROLES = 10;
    const MAX_USERS = 50;
    const MAX_IGNORED = 25;
    const DESCRIPTION = "Roles Square gives when people join, and the ones it gives back when they return.";
    const DELAYS = [
        { value: "0", label: "Right away" },
        { value: "60", label: "1 minute" },
        { value: "300", label: "5 minutes" },
        { value: "600", label: "10 minutes" },
        { value: "1800", label: "30 minutes" },
        { value: "3600", label: "1 hour" },
    ];

    const details = getDetails();
    const guild = $derived(data.guild.id);
    const savedQuery = $derived(remote.autorole(guild));
    const rolesQuery = $derived(settings.guildRoles(guild));
    const permsQuery = $derived(settings.botPermissions(guild));

    const saved = $derived(savedQuery.current!);
    const roles = $derived(rolesQuery.current!);
    const perms = $derived(new SquarePermissions(permsQuery.current));
    const screeningOn = $derived(perms.hasFeature("MEMBER_VERIFICATION_GATE_ENABLED"));

    let humans = $derived(saved.roleIds);
    let bots = $derived(saved.botRoleIds);
    let split = $derived(saved.splitBots);
    let users = $derived<AutoroleUser[]>(saved.users);
    let delay = $derived(saved.delay);
    let screening = $derived(saved.waitForScreening);
    let sticky = $derived(saved.sticky);
    let ignored = $derived(saved.stickyIgnoreIds);

    const sameRoles = (a: string[], b: string[]) => a.length === b.length && a.every((id) => b.includes(id));
    const sameUsers = (a: AutoroleUser[], b: AutoroleUser[]) =>
        a.length === b.length && a.every((entry) => b.some((other) => other.user.id === entry.user.id && sameRoles(other.roleIds, entry.roleIds)));

    const changes = $derived({
        ...(!sameRoles(humans, saved.roleIds) && { roleIds: humans }),
        ...(!sameRoles(bots, saved.botRoleIds) && { botRoleIds: bots }),
        ...(split !== saved.splitBots && { splitBots: split }),
        ...(!sameUsers(users, saved.users) && {
            users: users.map((entry) => ({ userId: entry.user.id, roleIds: entry.roleIds })),
        }),
        ...(delay !== saved.delay && { delay }),
        ...(screening !== saved.waitForScreening && { waitForScreening: screening }),
        ...(sticky !== saved.sticky && { sticky }),
        ...(!sameRoles(ignored, saved.stickyIgnoreIds) && { stickyIgnoreIds: ignored }),
    });
    const invalid = $derived(users.some((entry) => !entry.roleIds.length) ? "Pick at least one role for everyone on the list." : "");

    function discard() {
        humans = saved.roleIds;
        bots = saved.botRoleIds;
        split = saved.splitBots;
        users = saved.users;
        delay = saved.delay;
        screening = saved.waitForScreening;
        sticky = saved.sticky;
        ignored = saved.stickyIgnoreIds;
    }

    const roleName = $derived(new Map(roles.map((role) => [role.id, role.name])));
    const keep = $derived([...saved.roleIds, ...saved.botRoleIds, ...saved.users.flatMap((entry) => entry.roleIds)]);
    const givable = $derived(givableRoles(roles, perms, keep));
    const ignoreChoices = $derived(roleOptions(roles));

    const isDefault = $derived(
        !saved.roleIds.length &&
            !saved.botRoleIds.length &&
            !saved.splitBots &&
            !saved.users.length &&
            !saved.delay &&
            !saved.waitForScreening &&
            !saved.sticky &&
            !saved.stickyIgnoreIds.length,
    );

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
                    options={givable.options}
                    note={givable.note}
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

<QueryGate queries={[savedQuery, rolesQuery, permsQuery]} title="AutoRole" description={DESCRIPTION} actions>
    {#snippet skeleton()}<PageSkeleton groups={[{ rows: 3 }, { rows: 2 }, { rows: 2 }, { rows: 2 }]} />{/snippet}
    <div class="flex flex-col gap-6">
        <PageHeading title="AutoRole" description={DESCRIPTION}>
            {#snippet actions()}
                <ResetButton
                    title="Reset AutoRole?"
                    done="AutoRole reset"
                    description="This clears every join role and turns off the wait and sticky roles. Nobody loses a role they already have, and roles kept for people who left are forgotten."
                    disabled={isDefault}
                    reset={() => remote.resetAutorole(guild)}
                    apply={(next) => savedQuery.set(next)}
                />
            {/snippet}
        </PageHeading>

        {#if !perms.has("ManageRoles")}
            <PermissionNotice label="Square can't give roles here" permission="ManageRoles" />
        {/if}

        <SettingGroup title="Join roles" description="Square gives these out when someone joins.">
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
                    <Select
                        title="Member roles"
                        placeholder="Add a role"
                        options={givable.options}
                        note={givable.note}
                        multiple
                        max={MAX_ROLES}
                        bind:values={humans}
                    />
                </SettingRow>
                <SettingRow label="Bots" description="Bots someone adds." icon={MaterialSymbolsSmartToyRounded}>
                    <Select
                        title="Bot roles"
                        placeholder="Add a role"
                        options={givable.options}
                        note={givable.note}
                        multiple
                        max={MAX_ROLES}
                        bind:values={bots}
                    />
                </SettingRow>
            {:else}
                <SettingRow label="Everyone" description="Members and bots alike." icon={MaterialSymbolsGroupRounded}>
                    <Select
                        title="Join roles"
                        placeholder="Add a role"
                        options={givable.options}
                        note={givable.note}
                        multiple
                        max={MAX_ROLES}
                        bind:values={humans}
                    />
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
                            {#if !entry.roleIds.length}<Chip tone="danger" size="sm">No roles picked</Chip>{/if}
                        </span>
                        {#if entry.roleIds.length}
                            <span class="truncate text-sm text-gray-400">
                                {entry.roleIds.map((id) => roleName.get(id) ?? "Unknown role").join(", ")}
                            </span>
                        {/if}
                    </span>
                    <MaterialSymbolsChevronRightRounded class="size-5 shrink-0 text-gray-400" />
                </button>
            {:else}
                <p class="p-4 text-sm text-gray-400">No one added yet.</p>
            {/each}
        </SettingGroup>

        <SettingGroup title="Timing" description="When Square gives the join roles. Extra roles for people follow the same timing.">
            <SettingRow
                label="Wait before giving"
                description="Gives people time to read the rules first. Leaving before then means no roles."
                icon={MaterialSymbolsScheduleRounded}
            >
                <Select
                    title="Wait before giving"
                    options={DELAYS}
                    bind:value={() => String(delay), (next) => next !== null && (delay = Number(next))}
                />
            </SettingRow>
            <SettingRow
                label="Wait for rules screening"
                description="With Discord's rules screening on, roles come only after someone agrees to the rules. Bots never wait."
                icon={MaterialSymbolsHowToRegRounded}
                layout="inline"
            >
                <Tooltip content={screeningOn ? null : "Rules screening is off in this server, so there's nothing to wait for."}>
                    <Toggle label="Wait for rules screening" disabled={!screeningOn && !screening} bind:checked={screening} />
                </Tooltip>
            </SettingRow>
        </SettingGroup>

        <SettingGroup title="Sticky roles" description="Give people back the roles they had when they left, so leaving can't shake off a muted role.">
            <SettingRow
                label="Give roles back"
                description={saved.sticky && saved.kept
                    ? `Square is keeping roles for ${formatCount(saved.kept)} ${saved.kept === 1 ? "person" : "people"}. Turning this off forgets them.`
                    : "Square remembers the roles of people who leave from now on. They come back right away, without waiting."}
                icon={MaterialSymbolsHistoryRounded}
                layout="inline"
            >
                <Tooltip content={perms.reason("ManageRoles")}>
                    <Toggle label="Give roles back" disabled={!perms.has("ManageRoles") && !sticky} bind:checked={sticky} />
                </Tooltip>
            </SettingRow>
            {#if sticky}
                <SettingRow label="Never give back" description="Roles left out when someone returns." icon={MaterialSymbolsBlockRounded}>
                    <Select title="Never give back" placeholder="No roles" options={ignoreChoices} multiple max={MAX_IGNORED} bind:values={ignored} />
                </SettingRow>
            {/if}
        </SettingGroup>
    </div>

    <SaveBar dirty={Object.keys(changes).length > 0} {invalid} onsave={() => remote.updateAutorole({ guild, ...changes })} ondiscard={discard} />
</QueryGate>
