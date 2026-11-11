<script lang="ts">
    import PageHeading from "#lib/components/PageHeading.svelte";
    import ResetButton from "#lib/components/ResetButton.svelte";
    import SaveBar from "#lib/components/SaveBar.svelte";
    import Select, { type Option } from "#lib/components/ui/Select.svelte";
    import * as settings from "#lib/settings.remote.ts";
    import MaterialSymbolsBlockRounded from "~icons/material-symbols/block-rounded";
    import MaterialSymbolsCampaignRounded from "~icons/material-symbols/campaign-rounded";
    import MaterialSymbolsPermMediaRounded from "~icons/material-symbols/perm-media-rounded";
    import MaterialSymbolsShieldPersonRounded from "~icons/material-symbols/shield-person-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    const OFF = "off";
    const off: Option = { value: OFF, label: "Off", icon: MaterialSymbolsBlockRounded };

    const guild = $derived(data.guild.id);
    const savedQuery = $derived(settings.generalSettings(guild));
    const rolesQuery = $derived(settings.guildRoles(guild));
    const channelsQuery = $derived(settings.guildChannels(guild));

    const saved = $derived(await savedQuery);
    const roles = $derived(await rolesQuery);
    const channels = $derived(await channelsQuery);

    let autorole = $derived<string | null>(saved.autoroleId ?? OFF);
    let mediaOnly = $derived<string | null>(saved.mediaOnlyChannelId ?? OFF);

    const pick = (value: string | null) => (value === OFF || value === null ? null : value);
    const changes = $derived({
        ...(pick(autorole) !== saved.autoroleId && { autoroleId: pick(autorole) }),
        ...(pick(mediaOnly) !== saved.mediaOnlyChannelId && { mediaOnlyChannelId: pick(mediaOnly) }),
    });

    function discard() {
        autorole = saved.autoroleId ?? OFF;
        mediaOnly = saved.mediaOnlyChannelId ?? OFF;
    }

    const roleOptions = $derived<Option[]>([
        off,
        ...roles
            .filter((role) => role.assignable || role.id === saved.autoroleId)
            .map((role) => ({ value: role.id, label: role.name, color: role.color ?? "var(--color-mist-400)" })),
    ]);

    const categories = $derived(new Map(channels.filter((channel) => channel.type === "category").map((channel) => [channel.id, channel])));
    const channelOptions = $derived<Option[]>([
        off,
        ...channels
            .filter((channel) => channel.type === "text" || channel.type === "news")
            .map((channel) => ({ channel, category: channel.parentId ? categories.get(channel.parentId) : undefined }))
            .sort((a, b) => (a.category?.position ?? -1) - (b.category?.position ?? -1) || a.channel.position - b.channel.position)
            .map(({ channel, category }) => ({
                value: channel.id,
                label: channel.name,
                icon: channel.type === "news" ? MaterialSymbolsCampaignRounded : MaterialSymbolsTagRounded,
                hint: category?.name,
            })),
    ]);

    const isDefault = $derived(saved.autoroleId === null && saved.mediaOnlyChannelId === null);
</script>

{#snippet setting(icon: typeof MaterialSymbolsTagRounded, title: string, description: string)}
    {@const Icon = icon}
    <div class="flex items-start gap-4">
        <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-accent">
            <Icon class="size-6" />
        </span>
        <div class="flex min-w-0 flex-col gap-1">
            <h2 class="font-display text-xl font-semibold">{title}</h2>
            <p class="text-sm text-mist-400">{description}</p>
        </div>
    </div>
{/snippet}

<div class="flex flex-col gap-8">
    <PageHeading title="General" description="The basics Square handles for {data.guild.name}.">
        {#snippet actions()}
            <ResetButton
                title="Reset general settings?"
                description="This turns off the auto role and the media-only channel. Nobody loses a role they already have."
                disabled={isDefault}
                reset={() => settings.resetGeneral(guild)}
                apply={(next) => savedQuery.set(next)}
            />
        {/snippet}
    </PageHeading>

    <div class="grid gap-4 lg:grid-cols-2">
        <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
            {@render setting(MaterialSymbolsShieldPersonRounded, "Auto role", "Square gives this role to everyone who joins.")}
            <Select title="Auto role" options={roleOptions} bind:value={autorole} />
        </section>
        <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
            {@render setting(
                MaterialSymbolsPermMediaRounded,
                "Media-only channel",
                "Square deletes messages there without a file or link. Members with Manage Messages can still chat.",
            )}
            <Select title="Media-only channel" options={channelOptions} bind:value={mediaOnly} />
        </section>
    </div>
</div>

<SaveBar dirty={Object.keys(changes).length > 0} onsave={() => settings.updateGeneral({ guild, ...changes })} ondiscard={discard} />
