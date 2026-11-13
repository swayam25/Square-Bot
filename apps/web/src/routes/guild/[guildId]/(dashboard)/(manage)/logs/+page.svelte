<script lang="ts">
    import PageHeading from "#lib/components/PageHeading.svelte";
    import PageSkeleton from "#lib/components/PageSkeleton.svelte";
    import QueryGate from "#lib/components/QueryGate.svelte";
    import ResetButton from "#lib/components/ResetButton.svelte";
    import SaveBar from "#lib/components/SaveBar.svelte";
    import SettingGroup from "#lib/components/SettingGroup.svelte";
    import SettingRow from "#lib/components/SettingRow.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import { OFF, off, picked, textChannelOptions } from "#lib/options.ts";
    import * as settings from "#lib/settings.remote.ts";
    import type { LogChannels } from "@square/api-client";
    import type { Component } from "svelte";
    import MaterialSymbolsAddModeratorRounded from "~icons/material-symbols/add-moderator-rounded";
    import MaterialSymbolsChatRounded from "~icons/material-symbols/chat-rounded";
    import MaterialSymbolsConfirmationNumberRounded from "~icons/material-symbols/confirmation-number-rounded";
    import MaterialSymbolsDescriptionRounded from "~icons/material-symbols/description-rounded";
    import MaterialSymbolsGavelRounded from "~icons/material-symbols/gavel-rounded";
    import MaterialSymbolsGroupRounded from "~icons/material-symbols/group-rounded";
    import MaterialSymbolsHomeStorageRounded from "~icons/material-symbols/home-storage-rounded";
    import MaterialSymbolsLinkRounded from "~icons/material-symbols/link-rounded";
    import MaterialSymbolsShieldPersonRounded from "~icons/material-symbols/shield-person-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import MaterialSymbolsVolumeUpRounded from "~icons/material-symbols/volume-up-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    type Key = keyof LogChannels;
    const LOGS: { key: Key; label: string; description: string; icon: Component }[] = [
        { key: "moderation", label: "Moderation", description: "Bans, unbans and timeouts.", icon: MaterialSymbolsGavelRounded },
        { key: "members", label: "Members", description: "Joins, leaves, nickname and role changes.", icon: MaterialSymbolsGroupRounded },
        { key: "messages", label: "Messages", description: "Edited and deleted messages.", icon: MaterialSymbolsChatRounded },
        { key: "channels", label: "Channels", description: "Channels and threads created, changed or deleted.", icon: MaterialSymbolsTagRounded },
        { key: "roles", label: "Roles", description: "Roles created, changed or deleted.", icon: MaterialSymbolsShieldPersonRounded },
        { key: "server", label: "Server", description: "Server profile, emoji and sticker changes.", icon: MaterialSymbolsHomeStorageRounded },
        {
            key: "voice",
            label: "Voice",
            description: "Members joining, leaving and moving between voice channels.",
            icon: MaterialSymbolsVolumeUpRounded,
        },
        { key: "invites", label: "Invites", description: "Invite links created or deleted.", icon: MaterialSymbolsLinkRounded },
        { key: "automod", label: "AutoMod", description: "Actions taken by Discord's AutoMod.", icon: MaterialSymbolsAddModeratorRounded },
        {
            key: "tickets",
            label: "Tickets",
            description: "Tickets opened, claimed and closed, with transcripts.",
            icon: MaterialSymbolsConfirmationNumberRounded,
        },
    ];

    const guild = $derived(data.guild.id);
    const savedQuery = $derived(settings.logSettings(guild));
    const channelsQuery = $derived(settings.guildChannels(guild));

    const saved = $derived(savedQuery.current!);
    const channels = $derived(channelsQuery.current!);

    const fromSaved = () => Object.fromEntries(LOGS.map(({ key }) => [key, saved.channels[key] ?? OFF])) as Record<Key, string | null>;
    let drafts = $derived(fromSaved());

    const changes = $derived(
        Object.fromEntries(
            LOGS.filter(({ key }) => picked(drafts[key]) !== (saved.channels[key] ?? null)).map(({ key }) => [key, picked(drafts[key])]),
        ),
    );

    const choices = $derived([off(), ...textChannelOptions(channels)]);

    const shared = $derived(new Set(Object.values(drafts)).size === 1 ? drafts.moderation : null);
    const setAll = (value: string | null) =>
        value && (drafts = Object.fromEntries(LOGS.map(({ key }) => [key, value])) as Record<Key, string | null>);

    const isDefault = $derived(LOGS.every(({ key }) => !saved.channels[key]));
</script>

<QueryGate queries={[savedQuery, channelsQuery]} title="Logs" description="Pick where Square posts what happens in {data.guild.name}." actions>
    {#snippet skeleton()}<PageSkeleton groups={[{ rows: 1, title: false }, { rows: LOGS.length }]} />{/snippet}
    <div class="flex flex-col gap-6">
        <PageHeading title="Logs" description="Pick where Square posts what happens in {data.guild.name}.">
            {#snippet actions()}
                <ResetButton
                    title="Turn every log off?"
                    done="Every log turned off"
                    description="Square stops posting logs. Nothing already posted is deleted."
                    label="Turn all off"
                    disabled={isDefault}
                    reset={() => settings.resetLogs(guild)}
                    apply={(next) => savedQuery.set(next)}
                />
            {/snippet}
        </PageHeading>

        <SettingGroup>
            <SettingRow
                label="Every log"
                description="Send all of them to one channel, then change the ones you want somewhere else."
                icon={MaterialSymbolsDescriptionRounded}
            >
                <Select title="Every log" placeholder="Different channels" options={choices} bind:value={() => shared, setAll} />
            </SettingRow>
        </SettingGroup>

        <SettingGroup title="Log channels">
            {#each LOGS as log (log.key)}
                <SettingRow label={log.label} description={log.description} icon={log.icon}>
                    <Select
                        title="{log.label} log"
                        options={choices}
                        bind:value={() => drafts[log.key], (value) => (drafts = { ...drafts, [log.key]: value })}
                    />
                </SettingRow>
            {/each}
        </SettingGroup>
    </div>

    <SaveBar
        dirty={Object.keys(changes).length > 0}
        onsave={() => settings.updateLogs({ guild, channels: changes })}
        ondiscard={() => (drafts = fromSaved())}
    />
</QueryGate>
