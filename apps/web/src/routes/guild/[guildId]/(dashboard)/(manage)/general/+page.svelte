<script lang="ts">
    import PageHeading from "#lib/components/PageHeading.svelte";
    import QueryGate from "#lib/components/QueryGate.svelte";
    import ResetButton from "#lib/components/ResetButton.svelte";
    import SaveBar from "#lib/components/SaveBar.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import { OFF, off, picked, roleOptions, textChannelOptions } from "#lib/options.ts";
    import * as settings from "#lib/settings.remote.ts";
    import MaterialSymbolsPermMediaRounded from "~icons/material-symbols/perm-media-rounded";
    import MaterialSymbolsShieldPersonRounded from "~icons/material-symbols/shield-person-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    const guild = $derived(data.guild.id);
    const savedQuery = $derived(settings.generalSettings(guild));
    const rolesQuery = $derived(settings.guildRoles(guild));
    const channelsQuery = $derived(settings.guildChannels(guild));

    const saved = $derived(savedQuery.current!);
    const roles = $derived(rolesQuery.current!);
    const channels = $derived(channelsQuery.current!);

    let autorole = $derived<string | null>(saved.autoroleId ?? OFF);
    let mediaOnly = $derived<string | null>(saved.mediaOnlyChannelId ?? OFF);

    const changes = $derived({
        ...(picked(autorole) !== saved.autoroleId && { autoroleId: picked(autorole) }),
        ...(picked(mediaOnly) !== saved.mediaOnlyChannelId && { mediaOnlyChannelId: picked(mediaOnly) }),
    });

    function discard() {
        autorole = saved.autoroleId ?? OFF;
        mediaOnly = saved.mediaOnlyChannelId ?? OFF;
    }

    const roleChoices = $derived([off(), ...roleOptions(roles, { assignable: true, keep: saved.autoroleId ? [saved.autoroleId] : [] })]);
    const channelChoices = $derived([off(), ...textChannelOptions(channels)]);

    const isDefault = $derived(saved.autoroleId === null && saved.mediaOnlyChannelId === null);
</script>

<QueryGate queries={[savedQuery, rolesQuery, channelsQuery]} title="General" description="The basics Square handles for {data.guild.name}.">
    <div class="flex flex-col gap-8">
        <PageHeading title="General" description="The basics Square handles for {data.guild.name}.">
            {#snippet actions()}
                <ResetButton
                    title="Reset general settings?"
                    done="General settings reset"
                    description="This turns off the auto role and the media-only channel. Nobody loses a role they already have."
                    disabled={isDefault}
                    reset={() => settings.resetGeneral(guild)}
                    apply={(next) => savedQuery.set(next)}
                />
            {/snippet}
        </PageHeading>

        <div class="grid gap-4 lg:grid-cols-2">
            <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
                <div class="flex items-start gap-4">
                    <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-accent">
                        <MaterialSymbolsShieldPersonRounded class="size-6" />
                    </span>
                    <div class="flex min-w-0 flex-1 flex-col gap-1">
                        <h2 class="font-display text-xl font-semibold">Auto role</h2>
                        <p class="text-sm text-mist-400">Square gives this role to everyone who joins.</p>
                    </div>
                </div>
                <Select title="Auto role" options={roleChoices} bind:value={autorole} />
            </section>
            <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
                <div class="flex items-start gap-4">
                    <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-accent">
                        <MaterialSymbolsPermMediaRounded class="size-6" />
                    </span>
                    <div class="flex min-w-0 flex-1 flex-col gap-1">
                        <h2 class="font-display text-xl font-semibold">Media-only channel</h2>
                        <p class="text-sm text-mist-400">
                            Square deletes messages there without a file or link. Members with Manage Messages can still chat.
                        </p>
                    </div>
                </div>
                <Select title="Media-only channel" options={channelChoices} bind:value={mediaOnly} />
            </section>
        </div>
    </div>

    <SaveBar dirty={Object.keys(changes).length > 0} onsave={() => settings.updateGeneral({ guild, ...changes })} ondiscard={discard} />
</QueryGate>
