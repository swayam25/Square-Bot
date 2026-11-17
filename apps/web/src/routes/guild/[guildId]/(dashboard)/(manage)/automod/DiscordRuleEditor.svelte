<script lang="ts">
    import SettingGroup from "#lib/components/dashboard/SettingGroup.svelte";
    import SettingRow from "#lib/components/dashboard/SettingRow.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import Toggle from "#lib/components/ui/Toggle.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { channelOptions, OFF, off, picked, roleOptions, textChannelOptions } from "#lib/settings/options.ts";
    import type { Channel, NativeRule, Role } from "@square/api-client";
    import MaterialSymbolsAlternateEmailRounded from "~icons/material-symbols/alternate-email-rounded";
    import MaterialSymbolsBlockRounded from "~icons/material-symbols/block-rounded";
    import MaterialSymbolsChatErrorRounded from "~icons/material-symbols/chat-error-rounded";
    import MaterialSymbolsCheckCircleRounded from "~icons/material-symbols/check-circle-rounded";
    import MaterialSymbolsDoNotDisturbOnRounded from "~icons/material-symbols/do-not-disturb-on-rounded";
    import MaterialSymbolsHourglassRounded from "~icons/material-symbols/hourglass-rounded";
    import MaterialSymbolsNotificationsRounded from "~icons/material-symbols/notifications-rounded";
    import MaterialSymbolsPowerSettingsNewRounded from "~icons/material-symbols/power-settings-new-rounded";
    import MaterialSymbolsRegularExpressionRounded from "~icons/material-symbols/regular-expression-rounded";
    import MaterialSymbolsShieldPersonRounded from "~icons/material-symbols/shield-person-rounded";
    import MaterialSymbolsShieldRounded from "~icons/material-symbols/shield-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import { DURATIONS, LIMITS, PRESETS, TRIGGERS, type Mode, type NativeProblems } from "./automod.ts";
    import WordList from "./WordList.svelte";

    let {
        rule = $bindable(),
        mode,
        channels,
        roles,
        canTimeout,
        problems,
    }: { rule: NativeRule; mode: Mode; channels: Channel[]; roles: Role[]; canTimeout: boolean; problems: NativeProblems } = $props();

    const WORD_EXAMPLE = ["badword", "*badword*"].join("\n");

    const advanced = $derived(mode === "advanced");
    const trigger = $derived(TRIGGERS[rule.trigger]);
    const words = $derived(rule.trigger === "keyword" || rule.trigger === "member_profile");
    const profile = $derived(rule.trigger === "member_profile");
    const timeouts = $derived(rule.trigger === "keyword" || rule.trigger === "mention_spam");

    const alertChoices = $derived([off("No alerts"), ...textChannelOptions(channels)]);
    const timeoutChoices = [off("No timeout"), ...DURATIONS];
    const exemptChannels = $derived(channelOptions(channels, ["text", "news", "forum", "voice", "stage_voice", "category"]));
    const roleChoices = $derived(roleOptions(roles));

    const togglePreset = (value: NativeRule["presets"][number], on: boolean) =>
        (rule.presets = on ? [...rule.presets.filter((entry) => entry !== value), value] : rule.presets.filter((entry) => entry !== value));
</script>

<div class="flex flex-col gap-6">
    <SettingGroup title={trigger.label} description={trigger.description}>
        {#if advanced}
            <SettingRow label="Name" description="Shown in Discord's AutoMod settings and alerts.">
                <Input aria-label="Rule name" maxlength={LIMITS.name} error={problems.name} bind:value={rule.name} />
            </SettingRow>
        {/if}
        <SettingRow
            label="On"
            description={rule.bySquare ? "Made from the Square dashboard." : "Made in Discord or by another bot. Changes here change it there too."}
            icon={MaterialSymbolsPowerSettingsNewRounded}
            layout="inline"
        >
            <Toggle label="Rule on" bind:checked={rule.enabled} />
        </SettingRow>
    </SettingGroup>

    <SettingGroup title="What it catches">
        {#if words}
            <SettingRow
                label="Words"
                description="One per line, not case sensitive. A plain word must stand alone. Add * to the start, end or both to also catch it inside longer words."
                icon={MaterialSymbolsShieldRounded}
                layout="below"
            >
                <WordList label="Words" placeholder={WORD_EXAMPLE} max={LIMITS.keywords} error={problems.keywords} bind:values={rule.keywords} />
            </SettingRow>
            {#if advanced}
                <SettingRow
                    label="Patterns"
                    description="Regular expressions in Rust's flavor, one per line."
                    icon={MaterialSymbolsRegularExpressionRounded}
                    layout="below"
                >
                    <WordList label="Patterns" mono max={LIMITS.patterns} error={problems.patterns} bind:values={rule.patterns} />
                </SettingRow>
            {/if}
        {:else if rule.trigger === "preset"}
            {#each PRESETS as preset (preset.value)}
                <SettingRow label={preset.label} description={preset.description} layout="inline">
                    <Toggle label={preset.label} bind:checked={() => rule.presets.includes(preset.value), (on) => togglePreset(preset.value, on)} />
                </SettingRow>
            {/each}
        {:else if rule.trigger === "mention_spam"}
            <SettingRow
                label="Most mentions"
                description="Different people and roles in one message. More than this is caught."
                icon={MaterialSymbolsAlternateEmailRounded}
            >
                <Input
                    type="number"
                    min={1}
                    max={LIMITS.mentions}
                    step={1}
                    aria-label="Most mentions"
                    error={problems.mentionLimit}
                    bind:value={rule.mentionLimit}
                />
            </SettingRow>
            {#if advanced}
                <SettingRow
                    label="Raid protection"
                    description="Discord also watches for many people mass pinging at once."
                    icon={MaterialSymbolsShieldRounded}
                    layout="inline"
                >
                    <Toggle label="Raid protection" bind:checked={rule.raidProtection} />
                </SettingRow>
            {/if}
        {:else}
            <p class="p-4 text-sm text-gray-400">Discord decides what counts as spam, there's nothing to set here.</p>
        {/if}
        {#if advanced && rule.trigger !== "spam" && rule.trigger !== "mention_spam"}
            <SettingRow
                label="Allowed words"
                description="One per line. Messages are never caught for these."
                icon={MaterialSymbolsCheckCircleRounded}
                layout="below"
            >
                <WordList
                    label="Allowed words"
                    max={rule.trigger === "preset" ? LIMITS.presetAllow : LIMITS.allow}
                    error={problems.allowList}
                    bind:values={rule.allowList}
                />
            </SettingRow>
        {/if}
    </SettingGroup>

    <SettingGroup title="What happens">
        {#if profile}
            <SettingRow
                label="Keep them quiet"
                description="They can't send messages, join voice or react until they fix their profile."
                icon={MaterialSymbolsDoNotDisturbOnRounded}
                layout="inline"
            >
                <Toggle label="Keep them quiet" bind:checked={rule.blockInteraction} />
            </SettingRow>
        {:else}
            <SettingRow label="Block the message" description="It never shows up in the channel." icon={MaterialSymbolsBlockRounded} layout="inline">
                <Toggle label="Block the message" bind:checked={rule.block} />
            </SettingRow>
            {#if advanced && rule.block}
                <SettingRow label="Note to them" description="Shown to the sender when a message is blocked." icon={MaterialSymbolsChatErrorRounded}>
                    <Input
                        aria-label="Note to them"
                        placeholder="Discord's default"
                        maxlength={LIMITS.message}
                        error={problems.blockMessage}
                        bind:value={() => rule.blockMessage ?? "", (next) => (rule.blockMessage = next || null)}
                    />
                </SettingRow>
            {/if}
        {/if}
        <SettingRow label="Alert channel" description="Discord posts what was caught here." icon={MaterialSymbolsNotificationsRounded}>
            <Select
                title="Alert channel"
                options={alertChoices}
                bind:value={() => rule.alertChannelId ?? OFF, (next) => (rule.alertChannelId = picked(next))}
            />
        </SettingRow>
        {#if timeouts}
            <SettingRow label="Timeout" description="How long the sender can't chat afterwards." icon={MaterialSymbolsHourglassRounded}>
                <Tooltip content={canTimeout ? null : "Square needs the Timeout Members permission"} class="w-full">
                    <Select
                        title="Timeout"
                        options={timeoutChoices}
                        disabled={!canTimeout && !rule.timeoutSeconds}
                        class="w-full"
                        bind:value={
                            () => (rule.timeoutSeconds ? String(rule.timeoutSeconds) : OFF),
                            (next) => (rule.timeoutSeconds = next === OFF || next === null ? null : Number(next))
                        }
                    />
                </Tooltip>
            </SettingRow>
        {/if}
    </SettingGroup>

    {#if advanced}
        <SettingGroup title="Exceptions" description="Discord already skips admins and people with Manage Server.">
            <SettingRow label="Roles" description="People with these roles are never caught." icon={MaterialSymbolsShieldPersonRounded}>
                <Select
                    title="Exempt roles"
                    placeholder="No roles"
                    options={roleChoices}
                    multiple
                    max={LIMITS.nativeRoles}
                    bind:values={rule.exemptRoleIds}
                />
            </SettingRow>
            {#if !profile}
                <SettingRow
                    label="Channels"
                    description="Messages here are never caught. A category covers its channels."
                    icon={MaterialSymbolsTagRounded}
                >
                    <Select
                        title="Exempt channels"
                        placeholder="No channels"
                        options={exemptChannels}
                        multiple
                        max={LIMITS.nativeChannels}
                        bind:values={rule.exemptChannelIds}
                    />
                </SettingRow>
            {/if}
        </SettingGroup>
    {/if}
</div>
