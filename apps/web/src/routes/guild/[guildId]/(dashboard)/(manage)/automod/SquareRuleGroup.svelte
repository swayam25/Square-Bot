<script lang="ts">
    import SettingGroup from "#lib/components/dashboard/SettingGroup.svelte";
    import SettingRow from "#lib/components/dashboard/SettingRow.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import Toggle from "#lib/components/ui/Toggle.svelte";
    import { channelOptions, roleOptions, textChannelOptions } from "#lib/settings/options.ts";
    import type { Channel, Role, SquareRule } from "@square/api-client";
    import MaterialSymbolsChatErrorRounded from "~icons/material-symbols/chat-error-rounded";
    import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
    import MaterialSymbolsHardwareRounded from "~icons/material-symbols/hardware-rounded";
    import MaterialSymbolsShieldPersonRounded from "~icons/material-symbols/shield-person-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import MaterialSymbolsTimerRounded from "~icons/material-symbols/timer-rounded";
    import { KINDS, LIMITS, type Mode, type SquareProblems } from "./automod.ts";

    let {
        rule = $bindable(),
        mode,
        channels,
        roles,
        problems,
    }: { rule: SquareRule; mode: Mode; channels: Channel[]; roles: Role[]; problems: SquareProblems } = $props();

    const kind = $derived(KINDS[rule.kind]);
    const roleChoices = $derived(roleOptions(roles));
    const exemptChannels = $derived(channelOptions(channels, ["text", "news", "forum", "voice", "stage_voice", "category"]));
    const mediaChannels = $derived(textChannelOptions(channels));
</script>

<SettingGroup>
    <SettingRow label={kind.label} description={kind.description} icon={kind.icon} layout="inline">
        <Toggle label={kind.label} bind:checked={rule.enabled} />
    </SettingRow>
    {#if rule.enabled}
        {#if rule.kind === "media"}
            <SettingRow label="Channels" description="Where only files and links are allowed." icon={MaterialSymbolsTagRounded}>
                <Select
                    title="Media-only channels"
                    placeholder="Pick channels"
                    options={mediaChannels}
                    multiple
                    max={LIMITS.mediaChannels}
                    error={problems.channels}
                    bind:values={rule.channelIds}
                />
            </SettingRow>
        {/if}
        {#if kind.amount}
            <SettingRow label={kind.amount.label} description={kind.amount.description} icon={kind.icon}>
                <Input
                    type="number"
                    min={kind.amount.min}
                    max={kind.amount.max}
                    step={1}
                    aria-label={kind.amount.label}
                    error={problems.amount}
                    bind:value={rule.amount}
                />
            </SettingRow>
        {/if}
        {#if kind.seconds}
            <SettingRow label={kind.seconds.label} description={kind.seconds.description} icon={MaterialSymbolsTimerRounded}>
                <Input
                    type="number"
                    min={kind.seconds.min}
                    max={kind.seconds.max}
                    step={1}
                    aria-label={kind.seconds.label}
                    error={problems.seconds}
                    bind:value={rule.seconds}
                />
            </SettingRow>
        {/if}
        <SettingRow label="Delete the message" description="Square removes it right away." icon={MaterialSymbolsDeleteRounded} layout="inline">
            <Toggle label="Delete the message" bind:checked={rule.delete} />
        </SettingRow>
        <SettingRow
            label="Warn them"
            description="Adds a warning, which counts toward the punishments."
            icon={MaterialSymbolsHardwareRounded}
            layout="inline"
        >
            <Toggle label="Warn them" bind:checked={rule.warn} />
        </SettingRow>
        <SettingRow
            label="Tell them"
            description="A short note in the channel that goes away after 10 seconds."
            icon={MaterialSymbolsChatErrorRounded}
            layout="inline"
        >
            <Toggle label="Tell them" bind:checked={rule.notify} />
        </SettingRow>
        {#if mode === "advanced"}
            <SettingRow label="Skip roles" description="People with these roles are never caught." icon={MaterialSymbolsShieldPersonRounded}>
                <Select
                    title="Skip roles"
                    placeholder="No roles"
                    options={roleChoices}
                    multiple
                    max={LIMITS.roles}
                    bind:values={rule.exemptRoleIds}
                />
            </SettingRow>
            {#if rule.kind !== "media"}
                <SettingRow
                    label="Skip channels"
                    description="Messages here are never caught. A category covers its channels."
                    icon={MaterialSymbolsTagRounded}
                >
                    <Select
                        title="Skip channels"
                        placeholder="No channels"
                        options={exemptChannels}
                        multiple
                        max={LIMITS.channels}
                        bind:values={rule.exemptChannelIds}
                    />
                </SettingRow>
            {/if}
        {/if}
    {/if}
</SettingGroup>
