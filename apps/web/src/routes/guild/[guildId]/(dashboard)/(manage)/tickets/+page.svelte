<script lang="ts">
    import PageHeading from "#lib/components/PageHeading.svelte";
    import PageSkeleton from "#lib/components/PageSkeleton.svelte";
    import QueryGate from "#lib/components/QueryGate.svelte";
    import ResetButton from "#lib/components/ResetButton.svelte";
    import SaveBar from "#lib/components/SaveBar.svelte";
    import SettingGroup from "#lib/components/SettingGroup.svelte";
    import SettingRow from "#lib/components/SettingRow.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import ReadonlyField from "#lib/components/ui/ReadonlyField.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import Tabs from "#lib/components/ui/Tabs.svelte";
    import Toggle from "#lib/components/ui/Toggle.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { getDetails } from "#lib/details.svelte.ts";
    import { errorMessage } from "#lib/errors.ts";
    import { channelOptions, OFF, picked, roleOptions } from "#lib/options.ts";
    import * as settings from "#lib/settings.remote.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import MaterialSymbolsAutoAwesomeRounded from "~icons/material-symbols/auto-awesome-rounded";
    import MaterialSymbolsConfirmationNumberRounded from "~icons/material-symbols/confirmation-number-rounded";
    import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
    import MaterialSymbolsFolderRounded from "~icons/material-symbols/folder-rounded";
    import MaterialSymbolsSupportAgentRounded from "~icons/material-symbols/support-agent-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import MaterialSymbolsTaskAltRounded from "~icons/material-symbols/task-alt-rounded";
    import MaterialSymbolsTuneRounded from "~icons/material-symbols/tune-rounded";
    import MaterialSymbolsWebAssetRounded from "~icons/material-symbols/web-asset-rounded";
    import type { PageProps } from "./$types";
    import TicketList from "./TicketList.svelte";

    let { data }: PageProps = $props();

    const MAX_SUPPORT_ROLES = 10;
    const MAX_OPEN = 25;

    const details = getDetails();
    let tab = $state<"tickets" | "settings">("tickets");
    let openCount = $state(0);

    const guild = $derived(data.guild.id);
    const savedQuery = $derived(settings.ticketSettings(guild));
    const rolesQuery = $derived(settings.guildRoles(guild));
    const channelsQuery = $derived(settings.guildChannels(guild));

    const saved = $derived(savedQuery.current!);
    const roles = $derived(rolesQuery.current!);
    const channels = $derived(channelsQuery.current!);

    let category = $derived<string | null>(saved.categoryId ?? OFF);
    let supportRoles = $derived(saved.supportRoleIds);
    let maxOpen = $derived<number | null>(saved.maxOpen);
    const validMaxOpen = $derived(Number.isInteger(maxOpen) && maxOpen! >= 1 && maxOpen! <= MAX_OPEN);
    let confirmClose = $derived(saved.confirmClose);

    const sameRoles = (a: string[], b: string[]) => a.length === b.length && a.every((id) => b.includes(id));
    const changes = $derived({
        ...(picked(category) !== saved.categoryId && { categoryId: picked(category) }),
        ...(!sameRoles(supportRoles, saved.supportRoleIds) && { supportRoleIds: supportRoles }),
        ...(maxOpen !== saved.maxOpen && { maxOpen: maxOpen! }),
        ...(confirmClose !== saved.confirmClose && { confirmClose }),
    });
    const dirty = $derived(Object.keys(changes).length > 0);

    function discard() {
        category = saved.categoryId ?? OFF;
        supportRoles = saved.supportRoleIds;
        maxOpen = saved.maxOpen;
        confirmClose = saved.confirmClose;
    }

    const categoryChoices = $derived([
        { value: OFF, label: "Made by Square", icon: MaterialSymbolsAutoAwesomeRounded },
        ...channelOptions(channels, ["category"]),
    ]);
    const roleChoices = $derived(roleOptions(roles, { keep: saved.supportRoleIds }));

    const panelChannel = $derived(channels.find((channel) => channel.id === saved.panelChannelId));
    let creating = $state(false);

    async function createPanel() {
        creating = true;
        try {
            await settings.createTicketPanel(guild);
            toast.success("Ticket panel created");
        } catch (err) {
            toast.error(errorMessage(err, "Square couldn't create the panel. Try again."));
        } finally {
            creating = false;
        }
    }

    const warn = (notes: string[]) => notes.length && toast.warning(notes.join(" "));

    const isDefault = $derived(
        !saved.panelChannelId && !saved.categoryId && !saved.supportRoleIds.length && saved.maxOpen === 1 && saved.confirmClose,
    );
</script>

<QueryGate
    queries={[savedQuery, rolesQuery, channelsQuery]}
    title="Tickets"
    description="Private help channels between members and your staff in {data.guild.name}."
>
    {#snippet skeleton()}<PageSkeleton tabs table="filter" />{/snippet}
    <div class="flex flex-col gap-6">
        <PageHeading title="Tickets" description="Private help channels between members and your staff in {data.guild.name}." />

        <Tabs
            label="Tickets"
            tabs={[
                { value: "tickets", label: "Tickets", icon: MaterialSymbolsConfirmationNumberRounded, count: openCount || undefined },
                { value: "settings", label: "Settings", icon: MaterialSymbolsTuneRounded },
            ]}
            bind:value={
                () => tab,
                (next) => {
                    tab = next;
                    details.close();
                }
            }
        >
            {#if tab === "tickets"}
                <TicketList {guild} bind:open={openCount} />
            {:else}
                <div class="flex flex-col gap-6">
                    <SettingGroup title="Opening tickets">
                        {#snippet actions()}
                            <ResetButton
                                title="Reset ticket settings?"
                                done="Ticket settings reset"
                                description="This removes the ticket panel and puts every ticket setting back to its default. Open tickets stay open."
                                disabled={isDefault}
                                reset={() => settings.resetTickets(guild)}
                                apply={(next) => {
                                    warn(next.notes);
                                    savedQuery.set(next.settings);
                                    channelsQuery.refresh();
                                }}
                            />
                        {/snippet}
                        <SettingRow
                            label="Ticket panel"
                            description="A read-only channel with an Open a ticket button, so members don't need a command."
                            icon={MaterialSymbolsWebAssetRounded}
                        >
                            {#if saved.panelChannelId}
                                <div class="flex items-center gap-2">
                                    <ReadonlyField icon={MaterialSymbolsTagRounded} text={panelChannel?.name ?? "Unknown channel"} />
                                    <Tooltip content={dirty ? "Save or discard your changes first" : null}>
                                        <ResetButton
                                            title="Remove the ticket panel?"
                                            done="Ticket panel removed"
                                            description="Square deletes the panel's channel, or just the panel if the channel has other messages. Open tickets stay open."
                                            label="Remove"
                                            icon={MaterialSymbolsDeleteRounded}
                                            disabled={dirty}
                                            reset={() => settings.removeTicketPanel(guild)}
                                            apply={(next) => {
                                                warn(next.notes);
                                                savedQuery.set(next.settings);
                                                channelsQuery.refresh();
                                            }}
                                        />
                                    </Tooltip>
                                </div>
                            {:else}
                                <Tooltip content={dirty ? "Save or discard your changes first" : "Square creates #tickets for it"} class="w-full">
                                    <Button variant="primary" class="w-full" loading={creating} disabled={dirty} onclick={createPanel}>
                                        {#if !creating}<MaterialSymbolsAddRounded />{/if}{creating ? "Creating…" : "Create panel"}
                                    </Button>
                                </Tooltip>
                            {/if}
                        </SettingRow>
                        <SettingRow
                            label="Open tickets per member"
                            description="How many tickets one member can have open at once, from 1 to {MAX_OPEN}."
                            icon={MaterialSymbolsConfirmationNumberRounded}
                        >
                            <Input
                                type="number"
                                min={1}
                                max={MAX_OPEN}
                                step={1}
                                aria-label="Open tickets per member"
                                invalid={!validMaxOpen}
                                bind:value={maxOpen}
                            />
                        </SettingRow>
                        <SettingRow label="Category" description="Where new ticket channels go." icon={MaterialSymbolsFolderRounded}>
                            <Select title="Ticket category" options={categoryChoices} bind:value={category} />
                        </SettingRow>
                    </SettingGroup>

                    <SettingGroup title="Staff">
                        <SettingRow
                            label="Support roles"
                            description="These roles see every ticket and can claim, close and delete them."
                            icon={MaterialSymbolsSupportAgentRounded}
                        >
                            <Select
                                title="Support roles"
                                placeholder="Add a role"
                                options={roleChoices}
                                multiple
                                max={MAX_SUPPORT_ROLES}
                                bind:values={supportRoles}
                            />
                        </SettingRow>
                        <SettingRow
                            label="Confirm before closing"
                            description="Ask for a second press before a ticket closes."
                            icon={MaterialSymbolsTaskAltRounded}
                            layout="inline"
                        >
                            <Toggle label="Confirm before closing" bind:checked={confirmClose} />
                        </SettingRow>
                    </SettingGroup>
                </div>
            {/if}
        </Tabs>
    </div>

    <SaveBar
        {dirty}
        invalid={validMaxOpen ? "" : `Pick 1 to ${MAX_OPEN} open tickets per member.`}
        onsave={() => settings.updateTickets({ guild, ...changes })}
        ondiscard={discard}
    />
</QueryGate>
