<script lang="ts">
    import SettingGroup from "#lib/components/dashboard/SettingGroup.svelte";
    import SettingRow from "#lib/components/dashboard/SettingRow.svelte";
    import ColorField from "#lib/components/fields/ColorField.svelte";
    import DateTimeField, { type Preset } from "#lib/components/fields/DateTimeField.svelte";
    import DiscordTextField from "#lib/components/fields/DiscordTextField.svelte";
    import EmojiPicker from "#lib/components/fields/EmojiPicker.svelte";
    import UserPicker from "#lib/components/fields/UserPicker.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import ReadonlyField from "#lib/components/ui/ReadonlyField.svelte";
    import Segmented from "#lib/components/ui/Segmented.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import { focusRing } from "#lib/components/ui/styles.ts";
    import Toggle from "#lib/components/ui/Toggle.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { customUrl } from "#lib/emoji/emoji.ts";
    import { dateTime } from "#lib/format.ts";
    import { off, OFF, picked, roleOptions, textChannelOptions } from "#lib/settings/options.ts";
    import { moduleSettings } from "#lib/settings/settings.remote.ts";
    import type { Channel, Person, Role } from "@square/api-client";
    import { MediaQuery } from "svelte/reactivity";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import MaterialSymbolsBlockRounded from "~icons/material-symbols/block-rounded";
    import MaterialSymbolsBookmarkRounded from "~icons/material-symbols/bookmark-rounded";
    import MaterialSymbolsCalendarMonthRounded from "~icons/material-symbols/calendar-month-rounded";
    import MaterialSymbolsCheckRounded from "~icons/material-symbols/check-rounded";
    import MaterialSymbolsCrownRounded from "~icons/material-symbols/crown-rounded";
    import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
    import MaterialSymbolsFeaturedSeasonalAndGiftsRounded from "~icons/material-symbols/featured-seasonal-and-gifts-rounded";
    import MaterialSymbolsGroupRounded from "~icons/material-symbols/group-rounded";
    import MaterialSymbolsImageRounded from "~icons/material-symbols/image-rounded";
    import MaterialSymbolsLinkRounded from "~icons/material-symbols/link-rounded";
    import MaterialSymbolsMilitaryTechRounded from "~icons/material-symbols/military-tech-rounded";
    import MaterialSymbolsNotificationsActiveRounded from "~icons/material-symbols/notifications-active-rounded";
    import MaterialSymbolsPaletteRounded from "~icons/material-symbols/palette-rounded";
    import MaterialSymbolsPersonRounded from "~icons/material-symbols/person-rounded";
    import MaterialSymbolsSmartButtonRounded from "~icons/material-symbols/smart-button-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import MaterialSymbolsTimerRounded from "~icons/material-symbols/timer-rounded";
    import { bonusRow, LIMITS, lockedOnceEnded, roundedHour, STYLES, type Draft, type GiveawayStatus, type Problems } from "./giveaway.ts";
    import GiveawayPreview from "./GiveawayPreview.svelte";
    import ImageInput from "./ImageInput.svelte";

    let {
        draft = $bindable(),
        status,
        guild,
        you,
        channels,
        roles,
        problems,
        attempted,
        entries = 0,
        winners = [],
        endedAt = null,
        storedImage = null,
    }: {
        draft: Draft;
        status: GiveawayStatus | "new";
        guild: { id: string; name: string; iconUrl: string | null };
        you: Person;
        channels: Channel[];
        roles: Role[];
        problems: Problems;
        attempted: boolean;
        entries?: number;
        winners?: Person[];
        endedAt?: number | null;
        storedImage?: string | null;
    } = $props();

    const wide = new MediaQuery("min-width: 1280px", false);
    let tab = $state<"editor" | "preview">("editor");
    const modulesQuery = $derived(moduleSettings(guild.id));
    const invitesOff = $derived(modulesQuery.current ? !modulesQuery.current.invites : false);

    const HOUR = 60 * 60 * 1000;
    const DAY = 24 * HOUR;
    const YEAR = 365 * DAY;

    function lock(field: keyof Draft | "bonus"): string | null {
        if (status === "ended" && lockedOnceEnded.has(field)) return "This can't change once the giveaway has ended";
        if (status === "running" && (field === "channelId" || field === "startsAt")) return "This can't change once the giveaway has started";
        return null;
    }

    const EMPTY_ONLY = new Set<keyof Problems>(["channelId", "prize"]);
    const error = (field: keyof Problems) => (EMPTY_ONLY.has(field) && !attempted ? null : (problems[field] ?? null));

    const starts = () => (draft.startNow || draft.startsAt === null ? Date.now() : draft.startsAt);
    const endPresets: Preset[] = [
        { label: "1 hour", at: () => starts() + HOUR },
        { label: "1 day", at: () => roundedHour(starts()) + DAY },
        { label: "3 days", at: () => roundedHour(starts()) + 3 * DAY },
        { label: "1 week", at: () => roundedHour(starts()) + 7 * DAY },
        { label: "2 weeks", at: () => roundedHour(starts()) + 14 * DAY },
    ];
    const startPresets: Preset[] = [
        { label: "In 1 hour", at: () => roundedHour() + HOUR },
        { label: "Tomorrow", at: () => roundedHour() + DAY },
        { label: "In 3 days", at: () => roundedHour() + 3 * DAY },
        { label: "Next week", at: () => roundedHour() + 7 * DAY },
    ];

    function setStartNow(now: boolean) {
        draft.startNow = now;
        if (!now && draft.startsAt === null) draft.startsAt = roundedHour() + DAY;
    }

    const roleChoices = $derived(roleOptions(roles));
    const pingChoices = $derived([off("Nobody"), { value: guild.id, label: "@everyone", icon: MaterialSymbolsGroupRounded }, ...roleOptions(roles)]);
    const winnerChoices = $derived([off("None"), ...roleOptions(roles, { assignable: true, keep: draft.winnerRoleId ? [draft.winnerRoleId] : [] })]);
    const usedBonus = $derived(draft.bonusRoles.map((entry) => entry.roleId));

    const emoji = $derived.by(() => {
        const custom = /^<(a?):(\w+):(\d{17,20})>$/.exec(draft.buttonEmoji ?? "");
        return custom ? { id: custom[3]!, name: custom[2]!, animated: custom[1] === "a" } : null;
    });
</script>

{#if !wide.current}
    <Segmented
        label="Show"
        class="w-fit"
        options={[
            { value: "editor", label: "Editor" },
            { value: "preview", label: "Preview" },
        ]}
        bind:value={tab}
    />
{/if}

<div class="grid grid-cols-1 items-start gap-6 xl:grid-cols-2">
    <div class={["flex min-w-0 flex-col gap-6", !wide.current && tab !== "editor" && "hidden"]}>
        <SettingGroup title="Prize">
            <SettingRow label="Prize" description="The message's title." icon={MaterialSymbolsFeaturedSeasonalAndGiftsRounded}>
                <Input aria-label="Prize" placeholder="Discord Nitro" maxlength={LIMITS.prize} error={error("prize")} bind:value={draft.prize} />
            </SettingRow>
            <SettingRow label="Description" description="A few words under the title. Discord markdown works." layout="below">
                <DiscordTextField
                    aria-label="Description"
                    placeholder="What it is, who it's from, anything else"
                    maxlength={LIMITS.description}
                    {guild}
                    error={error("description")}
                    bind:value={draft.description}
                />
            </SettingRow>
            <SettingRow label="Winners" description="How many people win, from 1 to {LIMITS.winners}." icon={MaterialSymbolsCrownRounded}>
                <Tooltip content={lock("winnerCount")} class="w-full *:min-w-0 *:flex-1">
                    <Input
                        type="number"
                        min={1}
                        max={LIMITS.winners}
                        step={1}
                        aria-label="Winners"
                        disabled={!!lock("winnerCount")}
                        error={error("winnerCount")}
                        bind:value={draft.winnerCount}
                    />
                </Tooltip>
            </SettingRow>
            <SettingRow label="Host" description="Shown as the person giving it away." icon={MaterialSymbolsPersonRounded}>
                <div class="flex min-w-0 items-center gap-2">
                    <Chip class="min-w-0 shrink pl-1">
                        <Avatar src={(draft.host ?? you).avatarUrl} name={(draft.host ?? you).name} class="size-6" />
                        <span class="truncate">{(draft.host ?? you).name}</span>
                    </Chip>
                    <UserPicker
                        guild={guild.id}
                        title="Pick a host"
                        placeholder="Change"
                        humansOnly
                        exclude={[(draft.host ?? you).id]}
                        class="min-w-28 flex-1"
                        onpick={(user) => (draft.host = { id: user.id, name: user.name, avatarUrl: user.avatarUrl })}
                    />
                </div>
            </SettingRow>
        </SettingGroup>

        <SettingGroup title="Timing">
            <SettingRow label="Channel" description="Where the giveaway is posted." icon={MaterialSymbolsTagRounded}>
                <Tooltip content={lock("channelId")} class="w-full *:min-w-0 *:flex-1">
                    <Select
                        title="Channel"
                        placeholder="Pick a channel"
                        options={textChannelOptions(channels)}
                        disabled={!!lock("channelId")}
                        error={error("channelId")}
                        bind:value={draft.channelId}
                    />
                </Tooltip>
            </SettingRow>
            <SettingRow
                label="Starts"
                description="Post it now, or schedule it and Square posts it on time."
                icon={MaterialSymbolsCalendarMonthRounded}
            >
                {#if status === "new"}
                    <div class="flex flex-col gap-2">
                        <Segmented
                            label="When it starts"
                            class="w-fit"
                            options={[
                                { value: "now", label: "Now" },
                                { value: "later", label: "Later" },
                            ]}
                            bind:value={() => (draft.startNow ? "now" : "later"), (next) => setStartNow(next === "now")}
                        />
                        {#if !draft.startNow}
                            <DateTimeField
                                title="Start time"
                                min={Date.now()}
                                max={Date.now() + YEAR}
                                presets={startPresets}
                                error={error("startsAt")}
                                bind:value={draft.startsAt}
                            />
                        {/if}
                    </div>
                {:else if status === "scheduled"}
                    <DateTimeField
                        title="Start time"
                        min={Date.now()}
                        max={Date.now() + YEAR}
                        presets={startPresets}
                        error={error("startsAt")}
                        bind:value={draft.startsAt}
                    />
                {:else}
                    <Tooltip content={lock("startsAt")} class="w-full *:min-w-0 *:flex-1">
                        <ReadonlyField icon={MaterialSymbolsCalendarMonthRounded} text={dateTime.format(draft.startsAt ?? 0)} />
                    </Tooltip>
                {/if}
            </SettingRow>
            <SettingRow label="Ends" description="Square picks the winners at this time." icon={MaterialSymbolsTimerRounded}>
                <Tooltip content={lock("endsAt")} class="w-full *:min-w-0 *:flex-1">
                    <DateTimeField
                        title="End time"
                        disabled={!!lock("endsAt")}
                        min={Date.now()}
                        max={starts() + YEAR}
                        presets={endPresets}
                        error={error("endsAt")}
                        bind:value={draft.endsAt}
                    />
                </Tooltip>
            </SettingRow>
        </SettingGroup>

        <SettingGroup title="Who can enter">
            <SettingRow label="Required roles" description="Only people with these roles can enter." icon={MaterialSymbolsBookmarkRounded}>
                <Tooltip content={lock("requiredRoleIds")} class="w-full *:min-w-0 *:flex-1">
                    <Select
                        title="Required roles"
                        placeholder="Anyone can enter"
                        options={roleChoices}
                        multiple
                        max={LIMITS.roles}
                        disabled={!!lock("requiredRoleIds")}
                        bind:values={draft.requiredRoleIds}
                    />
                </Tooltip>
            </SettingRow>
            {#if draft.requiredRoleIds.length > 1}
                <SettingRow
                    label="Needs all of them"
                    description="Off, one of the roles is enough."
                    icon={MaterialSymbolsCheckRounded}
                    layout="inline"
                >
                    <Tooltip content={lock("requireAllRoles")} class="w-full *:min-w-0 *:flex-1">
                        <Toggle label="Needs all of them" disabled={!!lock("requireAllRoles")} bind:checked={draft.requireAllRoles} />
                    </Tooltip>
                </SettingRow>
            {/if}
            <SettingRow label="Blocked roles" description="People with any of these roles can't enter." icon={MaterialSymbolsBlockRounded}>
                <Tooltip content={lock("blockedRoleIds")} class="w-full *:min-w-0 *:flex-1">
                    <Select
                        title="Blocked roles"
                        placeholder="Nobody is blocked"
                        options={roleChoices}
                        multiple
                        max={LIMITS.roles}
                        disabled={!!lock("blockedRoleIds")}
                        bind:values={draft.blockedRoleIds}
                    />
                </Tooltip>
            </SettingRow>
            <SettingRow
                label="Account age"
                description="Days since their Discord account was made. 0 lets anyone in."
                icon={MaterialSymbolsPersonRounded}
            >
                <Tooltip content={lock("minAccountDays")} class="w-full *:min-w-0 *:flex-1">
                    <Input
                        type="number"
                        min={0}
                        max={LIMITS.days}
                        step={1}
                        aria-label="Account age in days"
                        disabled={!!lock("minAccountDays")}
                        error={error("minAccountDays")}
                        bind:value={draft.minAccountDays}
                    />
                </Tooltip>
            </SettingRow>
            <SettingRow label="Time in server" description="Days since they joined this server. 0 lets anyone in." icon={MaterialSymbolsGroupRounded}>
                <Tooltip content={lock("minMemberDays")} class="w-full *:min-w-0 *:flex-1">
                    <Input
                        type="number"
                        min={0}
                        max={LIMITS.days}
                        step={1}
                        aria-label="Time in server in days"
                        disabled={!!lock("minMemberDays")}
                        error={error("minMemberDays")}
                        bind:value={draft.minMemberDays}
                    />
                </Tooltip>
            </SettingRow>
            <SettingRow
                label="Invites"
                description="People they invited, counted by the Invites module. 0 lets anyone in."
                icon={MaterialSymbolsLinkRounded}
            >
                <Tooltip
                    content={lock("minInvites") ?? (invitesOff ? "Turn on the Invites module from the Overview page first" : null)}
                    class="w-full *:min-w-0 *:flex-1"
                >
                    <Input
                        type="number"
                        min={0}
                        max={LIMITS.invites}
                        step={1}
                        aria-label="Invites needed"
                        disabled={!!lock("minInvites") || invitesOff}
                        error={error("minInvites")}
                        bind:value={draft.minInvites}
                    />
                </Tooltip>
            </SettingRow>
        </SettingGroup>

        <SettingGroup
            title="Bonus entries"
            description="Extra entries make a win more likely. Someone with several of these roles gets the biggest bonus, not all of them."
        >
            <div class="flex flex-col gap-2 p-4">
                {#each draft.bonusRoles as entry, index (entry.key)}
                    <div class="flex items-center gap-2">
                        <div class="min-w-0 flex-1">
                            <Select
                                title="Bonus role"
                                placeholder="Pick a role"
                                options={roleChoices.filter((option) => option.value === entry.roleId || !usedBonus.includes(option.value))}
                                disabled={!!lock("bonus")}
                                error={attempted && !entry.roleId ? "Pick a role" : null}
                                bind:value={entry.roleId}
                            />
                        </div>
                        <div class="w-32 shrink-0">
                            <Input
                                type="number"
                                min={1}
                                max={LIMITS.entries}
                                step={1}
                                aria-label="Extra entries"
                                disabled={!!lock("bonus")}
                                error={entry.entries === null ||
                                (Number.isInteger(entry.entries) && entry.entries >= 1 && entry.entries <= LIMITS.entries)
                                    ? null
                                    : `Pick 1 to ${LIMITS.entries}`}
                                bind:value={entry.entries}
                            />
                        </div>
                        <Tooltip content={lock("bonus") ?? "Remove bonus"}>
                            <Button variant="ghost-danger" icon disabled={!!lock("bonus")} onclick={() => draft.bonusRoles.splice(index, 1)}>
                                <MaterialSymbolsDeleteRounded />
                            </Button>
                        </Tooltip>
                    </div>
                {/each}
                <Tooltip
                    content={lock("bonus") ?? (draft.bonusRoles.length >= LIMITS.roles ? `Up to ${LIMITS.roles} bonus roles` : null)}
                    class="w-fit"
                >
                    <Button disabled={!!lock("bonus") || draft.bonusRoles.length >= LIMITS.roles} onclick={() => draft.bonusRoles.push(bonusRow())}>
                        <MaterialSymbolsAddRounded />Add bonus role
                    </Button>
                </Tooltip>
            </div>
        </SettingGroup>

        <SettingGroup title="Look">
            <SettingRow label="Color" description="The stripe on the message's left edge." icon={MaterialSymbolsPaletteRounded} layout="below">
                <ColorField label="Stripe color" bind:value={draft.color} />
            </SettingRow>
            <SettingRow label="Image" description="A picture under the details. Upload one or paste a link." icon={MaterialSymbolsImageRounded}>
                <ImageInput bind:draft stored={storedImage} error={problems.imageUrl ?? null} />
            </SettingRow>
            <SettingRow
                label="Button"
                description="People press it to enter. The number of people in shows after a dot."
                icon={MaterialSymbolsSmartButtonRounded}
                layout="below"
            >
                <div class="flex flex-col gap-2">
                    <div class="flex items-center gap-2">
                        {#if draft.buttonEmoji}
                            <Tooltip content="Remove emoji">
                                <button
                                    type="button"
                                    class={[
                                        "flex size-12 shrink-0 cursor-pointer items-center justify-center rounded-full bg-gray-800 hover:bg-gray-700 md:size-10",
                                        focusRing,
                                    ]}
                                    onclick={() => (draft.buttonEmoji = null)}
                                >
                                    {#if emoji}
                                        <img
                                            src={customUrl({ id: emoji.id, animated: emoji.animated })}
                                            alt=":{emoji.name}:"
                                            class="size-6 object-contain"
                                        />
                                    {:else}
                                        <span class="font-emoji text-2xl/none">{draft.buttonEmoji}</span>
                                    {/if}
                                </button>
                            </Tooltip>
                        {:else}
                            <EmojiPicker {guild} placement="bottom-start" onpick={(text) => (draft.buttonEmoji = text)} />
                        {/if}
                        <Input
                            aria-label="Button label"
                            placeholder="No label, just the count"
                            maxlength={LIMITS.label}
                            bind:value={draft.buttonLabel}
                        />
                    </div>
                    <Segmented label="Button color" class="w-fit" options={STYLES} bind:value={draft.buttonStyle} />
                </div>
            </SettingRow>
        </SettingGroup>

        <SettingGroup title="Extras">
            <SettingRow label="Ping" description="Mention a role when the giveaway starts." icon={MaterialSymbolsNotificationsActiveRounded}>
                <Tooltip content={lock("pingRoleId")} class="w-full *:min-w-0 *:flex-1">
                    <Select
                        title="Ping"
                        options={pingChoices}
                        disabled={!!lock("pingRoleId")}
                        bind:value={() => draft.pingRoleId ?? OFF, (next) => (draft.pingRoleId = picked(next))}
                    />
                </Tooltip>
            </SettingRow>
            <SettingRow
                label="Winner role"
                description="Square gives winners this role, rerolled ones too."
                icon={MaterialSymbolsMilitaryTechRounded}
            >
                <Tooltip content={lock("winnerRoleId")} class="w-full *:min-w-0 *:flex-1">
                    <Select
                        title="Winner role"
                        options={winnerChoices}
                        disabled={!!lock("winnerRoleId")}
                        bind:value={() => draft.winnerRoleId ?? OFF, (next) => (draft.winnerRoleId = picked(next))}
                    />
                </Tooltip>
            </SettingRow>
        </SettingGroup>
    </div>

    <aside class={["flex min-w-0 flex-col gap-4 xl:sticky xl:top-0", !wide.current && tab !== "preview" && "hidden"]}>
        <h2 class="px-2 font-display text-lg font-semibold">Preview</h2>
        <GiveawayPreview {draft} {status} guild={guild.id} invites={!invitesOff} {you} {channels} {entries} {winners} {endedAt} {storedImage} />
    </aside>
</div>
