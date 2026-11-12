<script lang="ts">
    import Mention from "#lib/components/discord/Mention.svelte";
    import NowPlayingBanner from "#lib/components/NowPlayingBanner.svelte";
    import PageHeading from "#lib/components/PageHeading.svelte";
    import QueryGate from "#lib/components/QueryGate.svelte";
    import ResetButton from "#lib/components/ResetButton.svelte";
    import SaveBar from "#lib/components/SaveBar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
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
>
    <div class="flex flex-col gap-8">
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

        <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
            <div class="flex items-start gap-4">
                <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-accent">
                    <MaterialSymbolsQueueMusicRounded class="size-6" />
                </span>
                <div class="flex min-w-0 flex-1 flex-col gap-1">
                    <h2 class="font-display text-xl font-semibold">Request channel</h2>
                    <p class="text-sm text-mist-400">A channel with the player pinned. Anything members type there gets queued.</p>
                </div>
            </div>
            <div class="flex flex-col gap-4 md:flex-row md:items-center">
                {#if saved.requestChannelId}
                    <span class="flex h-12 min-w-0 flex-1 items-center gap-2 rounded-full bg-surface-2 px-4 text-sm font-medium md:h-10">
                        <MaterialSymbolsTagRounded class="size-5 shrink-0 text-mist-400" />
                        <span class="truncate">{requestChannel?.name ?? "Unknown channel"}</span>
                    </span>
                    <Tooltip content={dirty ? "Save or discard your changes first" : null}>
                        <ResetButton
                            title="Delete the request channel?"
                            done="Request channel deleted"
                            description="Square deletes the channel along with the player in it."
                            label="Delete channel"
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
                {:else}
                    <p class="min-w-0 flex-1 text-sm text-mist-400">
                        No request channel yet. Square creates <Mention name="music-requests" /> for it.
                    </p>
                    <Tooltip content={dirty ? "Save or discard your changes first" : null}>
                        <Button variant="primary" loading={creating} disabled={dirty} onclick={createRequestChannel}>
                            {#if !creating}<MaterialSymbolsAddRounded />{/if}{creating ? "Creating…" : "Create channel"}
                        </Button>
                    </Tooltip>
                {/if}
            </div>
        </section>

        <div class="grid gap-4 lg:grid-cols-2">
            <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
                <div class="flex items-start gap-4">
                    <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-accent">
                        <MaterialSymbolsAllInclusiveRounded class="size-6" />
                    </span>
                    <div class="flex min-w-0 flex-1 flex-col gap-1">
                        <h2 class="font-display text-xl font-semibold">24/7</h2>
                        <p class="text-sm text-mist-400">Square stays in this voice channel even when nothing is playing.</p>
                    </div>
                </div>
                <Select title="24/7 channel" options={voiceChoices} bind:value={stayChannel} />
            </section>
            <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
                <div class="flex items-start gap-4">
                    <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-accent">
                        <MaterialSymbolsHeadphonesRounded class="size-6" />
                    </span>
                    <div class="flex min-w-0 flex-1 flex-col gap-1">
                        <h2 class="font-display text-xl font-semibold">DJ mode</h2>
                        <p class="text-sm text-mist-400">
                            With it on, only DJ roles and server managers control the player. Others can still vote to skip.
                        </p>
                    </div>
                    <div class="shrink-0"><Toggle label="DJ mode" bind:checked={djMode} /></div>
                </div>

                <Select title="DJ roles" placeholder="Add a DJ role" options={roleChoices} multiple max={MAX_DJ_ROLES} bind:values={djRoles} />
            </section>
        </div>
    </div>

    <SaveBar {dirty} onsave={() => settings.updateMusic({ guild, ...changes })} ondiscard={discard} />
</QueryGate>
