<script lang="ts">
    import PageHeading from "#lib/components/dashboard/PageHeading.svelte";
    import PageSkeleton from "#lib/components/dashboard/PageSkeleton.svelte";
    import PermissionNotice from "#lib/components/dashboard/PermissionNotice.svelte";
    import QueryGate from "#lib/components/dashboard/QueryGate.svelte";
    import ResetButton from "#lib/components/dashboard/ResetButton.svelte";
    import SaveBar from "#lib/components/dashboard/SaveBar.svelte";
    import SettingGroup from "#lib/components/dashboard/SettingGroup.svelte";
    import SettingRow from "#lib/components/dashboard/SettingRow.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import Toggle from "#lib/components/ui/Toggle.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { SquarePermissions } from "#lib/permissions.ts";
    import { canUseAnyTextChannel, channelOptions, OFF, off, picked, roleOptions, usableTextChannels } from "#lib/settings/options.ts";
    import * as settings from "#lib/settings/settings.remote.ts";
    import type { LogPatch } from "@square/api-client";
    import { untrack } from "svelte";
    import MaterialSymbolsDescriptionRounded from "~icons/material-symbols/description-rounded";
    import MaterialSymbolsRobot2Rounded from "~icons/material-symbols/robot-2-rounded";
    import MaterialSymbolsShieldPersonRounded from "~icons/material-symbols/shield-person-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import type { PageProps } from "./$types";
    import { LIMITS, LOGS, type EventKey, type LogKey } from "./logs.ts";

    let { data }: PageProps = $props();

    const guild = $derived(data.guild.id);
    const savedQuery = $derived(settings.logSettings(guild));
    const channelsQuery = $derived(settings.guildChannels(guild));
    const rolesQuery = $derived(settings.guildRoles(guild));
    const permsQuery = $derived(settings.botPermissions(guild));

    const saved = $derived(savedQuery.current!);
    const channels = $derived(channelsQuery.current!);
    const roles = $derived(rolesQuery.current ?? []);
    const perms = $derived(new SquarePermissions(permsQuery.current));
    const auditReason = $derived(perms.reason("ViewAuditLog"));

    type Draft = {
        channels: Record<LogKey, string | null>;
        disabled: EventKey[];
        ignoredChannels: string[];
        ignoredRoles: string[];
        skipBots: boolean;
    };

    const fromSaved = (): Draft => ({
        channels: Object.fromEntries(LOGS.map(({ key }) => [key, saved.channels[key] ?? OFF])) as Record<LogKey, string | null>,
        disabled: [...saved.disabledEvents],
        ignoredChannels: [...saved.ignoredChannelIds],
        ignoredRoles: [...saved.ignoredRoleIds],
        skipBots: saved.skipBots,
    });
    let draft = $state<Draft>({ channels: {} as Draft["channels"], disabled: [], ignoredChannels: [], ignoredRoles: [], skipBots: true });
    $effect.pre(() => {
        if (!savedQuery.current) return;
        const next = fromSaved();
        untrack(() => (draft = next));
    });

    const sameSet = (a: string[], b: string[]) => a.length === b.length && a.every((item) => b.includes(item));

    const patch = $derived.by(() => {
        const body: LogPatch = {};
        const moved = LOGS.filter(({ key }) => picked(draft.channels[key]) !== (saved.channels[key] ?? null));
        if (moved.length) body.channels = Object.fromEntries(moved.map(({ key }) => [key, picked(draft.channels[key])]));
        if (!sameSet(draft.disabled, saved.disabledEvents)) body.disabledEvents = draft.disabled;
        if (!sameSet(draft.ignoredChannels, saved.ignoredChannelIds)) body.ignoredChannelIds = draft.ignoredChannels;
        if (!sameSet(draft.ignoredRoles, saved.ignoredRoleIds)) body.ignoredRoleIds = draft.ignoredRoles;
        if (draft.skipBots !== saved.skipBots) body.skipBots = draft.skipBots;
        return body;
    });

    const logChannels = $derived(usableTextChannels(channels, perms, "webhook", Object.values(saved.channels)));
    const choices = $derived([off(), ...logChannels.options]);
    const ignoreChannels = $derived(channelOptions(channels, ["text", "news", "forum", "media", "voice", "stage_voice", "category"]));
    const roleChoices = $derived(roleOptions(roles));

    const values = $derived(Object.values(draft.channels));
    const shared = $derived(new Set(values).size === 1 ? values[0]! : null);
    const setAll = (value: string | null) =>
        value && (draft.channels = Object.fromEntries(LOGS.map(({ key }) => [key, value])) as Record<LogKey, string | null>);

    const setEvent = (key: EventKey, on: boolean) =>
        (draft.disabled = on ? draft.disabled.filter((event) => event !== key) : [...draft.disabled, key]);

    const isDefault = $derived(
        LOGS.every(({ key }) => !saved.channels[key]) &&
            !saved.disabledEvents.length &&
            !saved.ignoredChannelIds.length &&
            !saved.ignoredRoleIds.length &&
            saved.skipBots,
    );
</script>

<QueryGate
    queries={[savedQuery, channelsQuery, rolesQuery, permsQuery]}
    title="Logs"
    description="Pick where Square posts what happens in {data.guild.name}."
    actions
>
    {#snippet skeleton()}<PageSkeleton groups={[{ rows: 1, title: false }, { rows: LOGS.length }]} />{/snippet}
    <div class="flex flex-col gap-6">
        <PageHeading title="Logs" description="Pick where Square posts what happens in {data.guild.name}.">
            {#snippet actions()}
                <ResetButton
                    title="Reset the logs?"
                    done="Logs reset"
                    description="Every log turns off, every event turns back on and nothing is ignored. Nothing already posted is deleted."
                    disabled={isDefault}
                    reset={() => settings.resetLogs(guild)}
                    apply={(next) => savedQuery.set(next)}
                />
            {/snippet}
        </PageHeading>

        {#if !canUseAnyTextChannel(channels, perms, "webhook")}
            <PermissionNotice label="Square can't post logs here" permission="ManageWebhooks" />
        {/if}
        {#if auditReason}
            <PermissionNotice
                label="Square can't see who did what"
                permission="ViewAuditLog"
                kept="Events that come from the audit log, like bans, role changes and server changes, are skipped until it has it."
            />
        {/if}

        <SettingGroup>
            <SettingRow
                label="Every log"
                description="Send all of them to one channel, then change the ones you want somewhere else."
                icon={MaterialSymbolsDescriptionRounded}
            >
                <Select
                    title="Every log"
                    placeholder="Different channels"
                    options={choices}
                    note={logChannels.note}
                    bind:value={() => shared, setAll}
                />
            </SettingRow>
        </SettingGroup>

        {#each LOGS as log (log.key)}
            <SettingGroup>
                <SettingRow label={log.label} description={log.description} icon={log.icon}>
                    <Select
                        title="{log.label} log"
                        options={choices}
                        note={logChannels.note}
                        bind:value={() => draft.channels[log.key], (value) => (draft.channels = { ...draft.channels, [log.key]: value })}
                    />
                </SettingRow>
                {#if picked(draft.channels[log.key])}
                    {#each log.events as event (event.key)}
                        <SettingRow label={event.label} description={event.description} icon={event.icon} layout="inline">
                            <Tooltip content={event.auditLog ? auditReason : null}>
                                <Toggle
                                    label={event.label}
                                    disabled={Boolean(event.auditLog && auditReason)}
                                    bind:checked={() => !draft.disabled.includes(event.key), (on) => setEvent(event.key, on)}
                                />
                            </Tooltip>
                        </SettingRow>
                    {/each}
                {/if}
            </SettingGroup>
        {/each}

        <SettingGroup
            title="Ignore"
            description="Hidden from the Members, Messages, Voice and Server logs. Moderation, AutoMod and Tickets always log everything."
        >
            <SettingRow
                label="Channels"
                description="Nothing that happens here is logged. A category covers its channels."
                icon={MaterialSymbolsTagRounded}
            >
                <Select
                    title="Ignored channels"
                    placeholder="No channels"
                    options={ignoreChannels}
                    multiple
                    max={LIMITS.channels}
                    bind:values={draft.ignoredChannels}
                />
            </SettingRow>
            <SettingRow label="Roles" description="Nothing people with these roles do is logged." icon={MaterialSymbolsShieldPersonRounded}>
                <Select
                    title="Ignored roles"
                    placeholder="No roles"
                    options={roleChoices}
                    multiple
                    max={LIMITS.roles}
                    bind:values={draft.ignoredRoles}
                />
            </SettingRow>
            <SettingRow
                label="Skip bots"
                description="Messages and voice activity from bots aren't logged."
                icon={MaterialSymbolsRobot2Rounded}
                layout="inline"
            >
                <Toggle label="Skip bots" bind:checked={draft.skipBots} />
            </SettingRow>
        </SettingGroup>
    </div>

    <SaveBar dirty={Object.keys(patch).length > 0} onsave={() => settings.updateLogs({ guild, ...patch })} ondiscard={() => (draft = fromSaved())} />
</QueryGate>
