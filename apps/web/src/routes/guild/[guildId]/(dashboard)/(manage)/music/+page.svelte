<script lang="ts">
    import NowPlayingBanner from "#lib/components/NowPlayingBanner.svelte";
    import PageHeading from "#lib/components/PageHeading.svelte";
    import PageSkeleton from "#lib/components/PageSkeleton.svelte";
    import QueryGate from "#lib/components/QueryGate.svelte";
    import ResetButton from "#lib/components/ResetButton.svelte";
    import SaveBar from "#lib/components/SaveBar.svelte";
    import SettingGroup from "#lib/components/SettingGroup.svelte";
    import SettingRow from "#lib/components/SettingRow.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import ReadonlyField from "#lib/components/ui/ReadonlyField.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import Toggle from "#lib/components/ui/Toggle.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { errorMessage } from "#lib/errors.ts";
    import { channelOptions, OFF, off, picked, roleOptions } from "#lib/options.ts";
    import * as settings from "#lib/settings.remote.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import MaterialSymbolsAllInclusiveRounded from "~icons/material-symbols/all-inclusive-rounded";
    import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
    import MaterialSymbolsHeadphonesRounded from "~icons/material-symbols/headphones-rounded";
    import MaterialSymbolsQueueMusicRounded from "~icons/material-symbols/queue-music-rounded";
    import MaterialSymbolsShieldPersonRounded from "~icons/material-symbols/shield-person-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    const guild = $derived(data.guild.id);

    const MAX_DJ_ROLES = 5;

    const savedQuery = $derived(settings.musicSettings(guild));
    const rolesQuery = $derived(settings.guildRoles(guild));
    const channelsQuery = $derived(settings.guildChannels(guild));

    const saved = $derived(savedQuery.current!);
    const roles = $derived(rolesQuery.current!);
    const channels = $derived(channelsQuery.current!);

    let stayChannel = $derived<string | null>(saved.stayChannelId ?? OFF);
    let djMode = $derived(saved.djMode);
    let djRoles = $derived(saved.djRoleIds);

    const sameRoles = (a: string[], b: string[]) => a.length === b.length && a.every((id) => b.includes(id));
    const changes = $derived({
        ...(picked(stayChannel) !== saved.stayChannelId && { stayChannelId: picked(stayChannel) }),
        ...(djMode !== saved.djMode && { djMode }),
        ...(!sameRoles(djRoles, saved.djRoleIds) && { djRoleIds: djRoles }),
    });
    const dirty = $derived(Object.keys(changes).length > 0);

    function discard() {
        stayChannel = saved.stayChannelId ?? OFF;
        djMode = saved.djMode;
        djRoles = saved.djRoleIds;
    }

    const voiceChoices = $derived([off(), ...channelOptions(channels, ["voice", "stage_voice"])]);
    const roleChoices = $derived(roleOptions(roles, { keep: saved.djRoleIds }));

    const requestChannel = $derived(channels.find((channel) => channel.id === saved.requestChannelId));
    let creating = $state(false);

    async function createRequestChannel() {
        creating = true;
        try {
            await settings.createRequestChannel(guild);
            toast.success("Request channel created");
        } catch (err) {
            toast.error(errorMessage(err, "Square couldn't create the channel. Try again."));
        } finally {
            creating = false;
        }
    }

    const warn = (notes: string[]) => notes.length && toast.warning(notes.join(" "));

    const isDefault = $derived(!saved.requestChannelId && !saved.stayChannelId && !saved.djMode && !saved.djRoleIds.length);
</script>

<QueryGate
    queries={[savedQuery, rolesQuery, channelsQuery]}
    title="Music"
    description="The request channel, 24/7 and who controls the player in {data.guild.name}."
    actions
>
    {#snippet skeleton()}
        <div class="flex flex-col gap-6">
            <NowPlayingBanner {guild} />
            <PageSkeleton groups={[{ rows: 2 }, { rows: 2 }]} />
        </div>
    {/snippet}
    <div class="flex flex-col gap-6">
        <PageHeading title="Music" description="The request channel, 24/7 and who controls the player in {data.guild.name}.">
            {#snippet actions()}
                <ResetButton
                    title="Reset music settings?"
                    done="Music settings reset"
                    description="This deletes the request channel, turns off 24/7 and DJ mode, and clears the DJ roles."
                    disabled={isDefault}
                    reset={() => settings.resetMusic(guild)}
                    apply={(next) => {
                        warn(next.notes);
                        savedQuery.set(next.settings);
                        channelsQuery.refresh();
                    }}
                />
            {/snippet}
        </PageHeading>

        <NowPlayingBanner {guild} />

        <SettingGroup title="Channels">
            <SettingRow
                label="Request channel"
                description="A channel with the player pinned. Anything members type there gets queued."
                icon={MaterialSymbolsQueueMusicRounded}
            >
                {#if saved.requestChannelId}
                    <div class="flex items-center gap-2">
                        <ReadonlyField icon={MaterialSymbolsTagRounded} text={requestChannel?.name ?? "Unknown channel"} />
                        <Tooltip content={dirty ? "Save or discard your changes first" : null}>
                            <ResetButton
                                title="Delete the request channel?"
                                done="Request channel deleted"
                                description="Square deletes the channel along with the player in it."
                                label="Delete"
                                icon={MaterialSymbolsDeleteRounded}
                                disabled={dirty}
                                reset={() => settings.removeRequestChannel(guild)}
                                apply={(next) => {
                                    warn(next.notes);
                                    savedQuery.set(next.settings);
                                    channelsQuery.refresh();
                                }}
                            />
                        </Tooltip>
                    </div>
                {:else}
                    <Tooltip content={dirty ? "Save or discard your changes first" : "Square creates #music-requests for it"} class="w-full">
                        <Button variant="primary" class="w-full" loading={creating} disabled={dirty} onclick={createRequestChannel}>
                            {#if !creating}<MaterialSymbolsAddRounded />{/if}{creating ? "Creating…" : "Create channel"}
                        </Button>
                    </Tooltip>
                {/if}
            </SettingRow>
            <SettingRow
                label="24/7"
                description="Square stays in this voice channel even when nothing is playing."
                icon={MaterialSymbolsAllInclusiveRounded}
            >
                <Select title="24/7 channel" options={voiceChoices} bind:value={stayChannel} />
            </SettingRow>
        </SettingGroup>

        <SettingGroup title="Who controls the player">
            <SettingRow
                label="DJ mode"
                description="Only DJ roles and server managers control the player. Others can still vote to skip."
                icon={MaterialSymbolsHeadphonesRounded}
                layout="inline"
            >
                <Toggle label="DJ mode" bind:checked={djMode} />
            </SettingRow>
            <SettingRow label="DJ roles" description="Members with these roles count as DJs." icon={MaterialSymbolsShieldPersonRounded}>
                <Select title="DJ roles" placeholder="Add a DJ role" options={roleChoices} multiple max={MAX_DJ_ROLES} bind:values={djRoles} />
            </SettingRow>
        </SettingGroup>
    </div>

    <SaveBar {dirty} onsave={() => settings.updateMusic({ guild, ...changes })} ondiscard={discard} />
</QueryGate>
