<script lang="ts">
    import SettingGroup from "#lib/components/dashboard/SettingGroup.svelte";
    import SettingRow from "#lib/components/dashboard/SettingRow.svelte";
    import ColorField from "#lib/components/fields/ColorField.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Segmented from "#lib/components/ui/Segmented.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import Toggle from "#lib/components/ui/Toggle.svelte";
    import { channelOptions, roleOptions, textChannelOptions } from "#lib/settings/options.ts";
    import type { Channel, Person, Role } from "@square/api-client";
    import { MediaQuery } from "svelte/reactivity";
    import MaterialSymbolsBlockRounded from "~icons/material-symbols/block-rounded";
    import MaterialSymbolsCalendarMonthRounded from "~icons/material-symbols/calendar-month-rounded";
    import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
    import MaterialSymbolsFilterAltRounded from "~icons/material-symbols/filter-alt-rounded";
    import MaterialSymbolsPaletteRounded from "~icons/material-symbols/palette-rounded";
    import MaterialSymbolsPersonRounded from "~icons/material-symbols/person-rounded";
    import MaterialSymbolsPowerSettingsNewRounded from "~icons/material-symbols/power-settings-new-rounded";
    import MaterialSymbolsSmartToyRounded from "~icons/material-symbols/smart-toy-rounded";
    import MaterialSymbolsStarRounded from "~icons/material-symbols/star-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import MaterialSymbolsThumbDownRounded from "~icons/material-symbols/thumb-down-rounded";
    import MaterialSymbolsTrendingDownRounded from "~icons/material-symbols/trending-down-rounded";
    import { AGES, LIMITS, type Draft, type Problems } from "./board.ts";
    import BoardPreview from "./BoardPreview.svelte";
    import EmojiList from "./EmojiList.svelte";

    let {
        draft = $bindable(),
        guild,
        you,
        channels,
        roles,
        taken,
        problems,
    }: {
        draft: Draft;
        guild: { id: string; name: string; iconUrl: string | null };
        you: Person;
        channels: Channel[];
        roles: Role[];
        // Channels other boards use
        taken: string[];
        problems: Problems;
    } = $props();

    const wide = new MediaQuery("min-width: 1280px", false);
    let tab = $state<"editor" | "preview">("editor");

    const boardChoices = $derived(textChannelOptions(channels).filter((option) => !taken.includes(option.value)));
    const sourceChoices = $derived(
        channelOptions(channels, ["text", "news", "forum", "voice", "stage_voice", "category"]).filter((option) => option.value !== draft.channelId),
    );
    const roleChoices = $derived(roleOptions(roles));
    const age = $derived(AGES.find((entry) => entry.days === draft.maxAgeDays)?.value ?? "any");
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
        <SettingGroup title="Board">
            <SettingRow label="Channel" description="Where starred messages are posted." icon={MaterialSymbolsTagRounded}>
                <Select title="Board channel" options={boardChoices} bind:value={() => draft.channelId, (next) => next && (draft.channelId = next)} />
            </SettingRow>
            <SettingRow
                label="On"
                description="Off, votes stop counting until you turn it back on."
                icon={MaterialSymbolsPowerSettingsNewRounded}
                layout="inline"
            >
                <Toggle label="Board on" bind:checked={draft.enabled} />
            </SettingRow>
            <SettingRow
                label="Delete with the original"
                description="When a starred message is deleted, its post goes too. Off, the post stays on the board."
                icon={MaterialSymbolsDeleteRounded}
                layout="inline"
            >
                <Toggle label="Delete with the original" bind:checked={draft.followDeletes} />
            </SettingRow>
        </SettingGroup>

        <SettingGroup title="Votes">
            <SettingRow
                label="Vote emojis"
                description="Each emoji is counted on its own, they don't add up. A post shows the one with the most votes."
                icon={MaterialSymbolsStarRounded}
                layout="below"
            >
                <EmojiList {guild} max={LIMITS.emojis} error={problems.emojis} bind:values={draft.emojis} />
            </SettingRow>
            <SettingRow
                label="Downvote emojis"
                description="Each person reacting with one takes a vote away. Leave empty for none."
                icon={MaterialSymbolsThumbDownRounded}
                layout="below"
            >
                <EmojiList {guild} max={LIMITS.emojis} error={problems.downvoteEmojis} bind:values={draft.downvoteEmojis} />
            </SettingRow>
            <SettingRow label="Votes needed" description="How many one emoji needs to get on the board." icon={MaterialSymbolsStarRounded}>
                <Input
                    type="number"
                    min={1}
                    max={LIMITS.votes}
                    step={1}
                    aria-label="Votes needed"
                    error={problems.threshold}
                    bind:value={draft.threshold}
                />
            </SettingRow>
            <SettingRow
                label="Remove when votes drop"
                description="Off, a post stays once it made it, whatever happens to its votes."
                icon={MaterialSymbolsTrendingDownRounded}
                layout="inline"
            >
                <Toggle label="Remove when votes drop" bind:checked={draft.dropOn} />
            </SettingRow>
            {#if draft.dropOn}
                <SettingRow label="Remove below" description="A post leaves the board when it has fewer votes than this.">
                    <Input
                        type="number"
                        min={1}
                        max={LIMITS.votes}
                        step={1}
                        aria-label="Remove below this many votes"
                        error={problems.dropBelow}
                        bind:value={draft.dropBelow}
                    />
                </SettingRow>
            {/if}
            <SettingRow label="Self votes" description="Let people vote for their own messages." icon={MaterialSymbolsPersonRounded} layout="inline">
                <Toggle label="Self votes" bind:checked={draft.selfVote} />
            </SettingRow>
        </SettingGroup>

        <SettingGroup title="Which messages">
            <SettingRow
                label="Channels"
                description="Where messages can be starred from. Pick a category to cover its channels."
                icon={MaterialSymbolsFilterAltRounded}
                layout="below"
            >
                <div class="flex flex-col gap-2">
                    <Segmented
                        label="Channels"
                        class="w-fit"
                        options={[
                            { value: "all", label: "All" },
                            { value: "only", label: "Only" },
                            { value: "except", label: "Except" },
                        ]}
                        bind:value={draft.channelMode}
                    />
                    {#if draft.channelMode !== "all"}
                        <Select
                            title={draft.channelMode === "only" ? "Only these channels" : "All but these channels"}
                            placeholder="Pick channels"
                            options={sourceChoices}
                            multiple
                            max={LIMITS.channels}
                            bind:values={draft.channelIds}
                        />
                    {/if}
                </div>
            </SettingRow>
            <SettingRow
                label="Bot messages"
                description="Let messages from bots and webhooks be starred."
                icon={MaterialSymbolsSmartToyRounded}
                layout="inline"
            >
                <Toggle label="Bot messages" bind:checked={draft.allowBots} />
            </SettingRow>
            <SettingRow label="Message age" description="Only messages newer than this can be starred." icon={MaterialSymbolsCalendarMonthRounded}>
                <Select
                    title="Message age"
                    options={AGES.map(({ value, label }) => ({ value, label }))}
                    bind:value={() => age, (next) => (draft.maxAgeDays = AGES.find((entry) => entry.value === next)?.days ?? null)}
                />
            </SettingRow>
            <SettingRow
                label="Blocked roles"
                description="People with these roles can't vote, and their messages can't be starred."
                icon={MaterialSymbolsBlockRounded}
            >
                <Select
                    title="Blocked roles"
                    placeholder="Nobody is blocked"
                    options={roleChoices}
                    multiple
                    max={LIMITS.roles}
                    bind:values={draft.blockedRoleIds}
                />
            </SettingRow>
        </SettingGroup>

        <SettingGroup title="Look">
            <SettingRow
                label="Color"
                description="The post's stripe. No color uses Square's orange."
                icon={MaterialSymbolsPaletteRounded}
                layout="below"
            >
                <ColorField label="Stripe color" bind:value={draft.color} />
            </SettingRow>
        </SettingGroup>
    </div>

    <aside class={["flex min-w-0 flex-col gap-4 xl:sticky xl:top-0", !wide.current && tab !== "preview" && "hidden"]}>
        <h2 class="px-2 font-display text-lg font-semibold">Preview</h2>
        <BoardPreview {draft} guild={guild.id} {you} {channels} />
    </aside>
</div>
