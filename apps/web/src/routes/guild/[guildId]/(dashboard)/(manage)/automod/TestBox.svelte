<script lang="ts">
    import SettingGroup from "#lib/components/dashboard/SettingGroup.svelte";
    import SettingRow from "#lib/components/dashboard/SettingRow.svelte";
    import DiscordTextField from "#lib/components/fields/DiscordTextField.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import { errorMessage } from "#lib/errors.ts";
    import { OFF, off, picked, textChannelOptions } from "#lib/settings/options.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import type { AutomodTestResult, Channel } from "@square/api-client";
    import MaterialSymbolsCheckCircleRounded from "~icons/material-symbols/check-circle-rounded";
    import MaterialSymbolsScienceRounded from "~icons/material-symbols/science-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import { testAutomod } from "./automod.remote.ts";

    let { guild, channels, dirty }: { guild: { id: string; name: string; iconUrl: string | null }; channels: Channel[]; dirty: boolean } = $props();

    const MAX = 4000;

    let content = $state("");
    let channel = $state<string | null>(OFF);
    let running = $state(false);
    let result = $state<AutomodTestResult | null>(null);

    const channelChoices = $derived([off("Any channel"), ...textChannelOptions(channels)]);

    async function run() {
        running = true;
        try {
            result = await testAutomod({ guild: guild.id, content, channelId: picked(channel) });
        } catch (err) {
            result = null;
            toast.error(errorMessage(err, "Square couldn't run the test. Try again."));
        } finally {
            running = false;
        }
    }
</script>

<div class="flex flex-col gap-6">
    <SettingGroup
        title="Try a message"
        description={dirty
            ? "Uses the saved rules. Save your changes first to test them."
            : "See what the saved rules would catch, without sending anything."}
    >
        <SettingRow label="Message" layout="below">
            <DiscordTextField aria-label="Message to test" {guild} maxlength={MAX} placeholder="Type a message" bind:value={content} />
        </SettingRow>
        <SettingRow label="Sent in" description="For media-only channels and skipped channels." icon={MaterialSymbolsTagRounded}>
            <Select title="Sent in" options={channelChoices} bind:value={channel} />
        </SettingRow>
        <div class="flex justify-end p-4">
            <Button variant="primary" loading={running} disabled={!content.trim()} onclick={run}>
                {#if !running}<MaterialSymbolsScienceRounded />{/if}{running ? "Testing…" : "Test"}
            </Button>
        </div>
    </SettingGroup>

    {#if result}
        <SettingGroup title="Result">
            {#each result.hits as hit, index (index)}
                <div class="flex flex-wrap items-center gap-2 p-4">
                    <Chip tone={hit.source === "discord" ? "violet" : "accent"} size="sm">{hit.source === "discord" ? "Discord" : "Square"}</Chip>
                    <span class="text-sm font-medium">{hit.rule}</span>
                    <span class="text-sm text-gray-400">{hit.detail}</span>
                </div>
            {:else}
                <EmptyState
                    compact
                    icon={MaterialSymbolsCheckCircleRounded}
                    title="Nothing caught"
                    text="None of the rules that can be tested here would act on this."
                />
            {/each}
            {#each result.skipped as note, index (index)}
                <p class="p-4 text-sm text-gray-400">{note}</p>
            {/each}
        </SettingGroup>
    {/if}
</div>
