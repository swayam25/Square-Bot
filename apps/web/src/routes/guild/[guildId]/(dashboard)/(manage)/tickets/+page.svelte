<script lang="ts">
    import Mention from "#lib/components/discord/Mention.svelte";
    import PageHeading from "#lib/components/PageHeading.svelte";
    import QueryGate from "#lib/components/QueryGate.svelte";
    import ResetButton from "#lib/components/ResetButton.svelte";
    import SaveBar from "#lib/components/SaveBar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import Toggle from "#lib/components/ui/Toggle.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { errorMessage } from "#lib/errors.ts";
    import { channelOptions, OFF, picked, roleOptions } from "#lib/options.ts";
    import * as settings from "#lib/settings.remote.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import type { TicketSettings } from "@square/api-client";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import MaterialSymbolsAutoAwesomeRounded from "~icons/material-symbols/auto-awesome-rounded";
    import MaterialSymbolsConfirmationNumberRounded from "~icons/material-symbols/confirmation-number-rounded";
    import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
    import MaterialSymbolsFolderRounded from "~icons/material-symbols/folder-rounded";
    import MaterialSymbolsSupportAgentRounded from "~icons/material-symbols/support-agent-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import MaterialSymbolsTaskAltRounded from "~icons/material-symbols/task-alt-rounded";
    import MaterialSymbolsWebAssetRounded from "~icons/material-symbols/web-asset-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    const MAX_SUPPORT_ROLES = 10;
    const MAX_OPEN = [1, 2, 3, 5] as const;

    const guild = $derived(data.guild.id);
    const savedQuery = $derived(settings.ticketSettings(guild));
    const rolesQuery = $derived(settings.guildRoles(guild));
    const channelsQuery = $derived(settings.guildChannels(guild));

    const saved = $derived(savedQuery.current!);
    const roles = $derived(rolesQuery.current!);
    const channels = $derived(channelsQuery.current!);

    let category = $derived<string | null>(saved.categoryId ?? OFF);
    let supportRoles = $derived(saved.supportRoleIds);
    let maxOpen = $derived<string | null>(String(saved.maxOpen));
    let confirmClose = $derived(saved.confirmClose);

    const sameRoles = (a: string[], b: string[]) => a.length === b.length && a.every((id) => b.includes(id));
    const changes = $derived({
        ...(picked(category) !== saved.categoryId && { categoryId: picked(category) }),
        ...(!sameRoles(supportRoles, saved.supportRoleIds) && { supportRoleIds: supportRoles }),
        ...(Number(maxOpen) !== saved.maxOpen && { maxOpen: Number(maxOpen) as TicketSettings["maxOpen"] }),
        ...(confirmClose !== saved.confirmClose && { confirmClose }),
    });
    const dirty = $derived(Object.keys(changes).length > 0);

    function discard() {
        category = saved.categoryId ?? OFF;
        supportRoles = saved.supportRoleIds;
        maxOpen = String(saved.maxOpen);
        confirmClose = saved.confirmClose;
    }

    const categoryChoices = $derived([
        { value: OFF, label: "Made by Square", icon: MaterialSymbolsAutoAwesomeRounded },
        ...channelOptions(channels, ["category"]),
    ]);
    const roleChoices = $derived(roleOptions(roles, { keep: saved.supportRoleIds }));
    const maxOpenChoices = MAX_OPEN.map((count) => ({ value: String(count), label: `${count} ${count === 1 ? "ticket" : "tickets"}` }));

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
    <div class="flex flex-col gap-8">
        <PageHeading title="Tickets" description="Private help channels between members and your staff in {data.guild.name}.">
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
        </PageHeading>

        <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
            <div class="flex items-start gap-4">
                <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-accent">
                    <MaterialSymbolsWebAssetRounded class="size-6" />
                </span>
                <div class="flex min-w-0 flex-1 flex-col gap-1">
                    <h2 class="font-display text-xl font-semibold">Ticket panel</h2>
                    <p class="text-sm text-mist-400">A read-only channel with an Open a ticket button, so members don't need a command.</p>
                </div>
            </div>
            <div class="flex flex-col gap-4 md:flex-row md:items-center">
                {#if saved.panelChannelId}
                    <span class="flex h-12 min-w-0 flex-1 items-center gap-2 rounded-full bg-surface-2 px-4 text-sm font-medium md:h-10">
                        <MaterialSymbolsTagRounded class="size-5 shrink-0 text-mist-400" />
                        <span class="truncate">{panelChannel?.name ?? "Unknown channel"}</span>
                    </span>
                    <Tooltip content={dirty ? "Save or discard your changes first" : null}>
                        <ResetButton
                            title="Remove the ticket panel?"
                            done="Ticket panel removed"
                            description="Square deletes the panel's channel, or just the panel if the channel has other messages. Open tickets stay open."
                            label="Remove panel"
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
                {:else}
                    <p class="min-w-0 flex-1 text-sm text-mist-400">No panel yet. Square creates <Mention name="tickets" /> for it.</p>
                    <Tooltip content={dirty ? "Save or discard your changes first" : null}>
                        <Button variant="primary" loading={creating} disabled={dirty} onclick={createPanel}>
                            {#if !creating}<MaterialSymbolsAddRounded />{/if}{creating ? "Creating…" : "Create panel"}
                        </Button>
                    </Tooltip>
                {/if}
            </div>
        </section>

        <div class="grid gap-4 lg:grid-cols-2">
            <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
                <div class="flex items-start gap-4">
                    <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-accent">
                        <MaterialSymbolsSupportAgentRounded class="size-6" />
                    </span>
                    <div class="flex min-w-0 flex-1 flex-col gap-1">
                        <h2 class="font-display text-xl font-semibold">Support roles</h2>
                        <p class="text-sm text-mist-400">These roles see every ticket and can claim, close and delete them.</p>
                    </div>
                </div>
                <Select
                    title="Support roles"
                    placeholder="Add a role"
                    options={roleChoices}
                    multiple
                    max={MAX_SUPPORT_ROLES}
                    bind:values={supportRoles}
                />
            </section>
            <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
                <div class="flex items-start gap-4">
                    <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-accent">
                        <MaterialSymbolsFolderRounded class="size-6" />
                    </span>
                    <div class="flex min-w-0 flex-1 flex-col gap-1">
                        <h2 class="font-display text-xl font-semibold">Category</h2>
                        <p class="text-sm text-mist-400">Where new ticket channels go.</p>
                    </div>
                </div>
                <Select title="Ticket category" options={categoryChoices} bind:value={category} />
            </section>
            <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
                <div class="flex items-start gap-4">
                    <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-accent">
                        <MaterialSymbolsConfirmationNumberRounded class="size-6" />
                    </span>
                    <div class="flex min-w-0 flex-1 flex-col gap-1">
                        <h2 class="font-display text-xl font-semibold">Open tickets per member</h2>
                        <p class="text-sm text-mist-400">How many tickets one member can have open at once.</p>
                    </div>
                </div>
                <Select title="Open tickets per member" options={maxOpenChoices} bind:value={maxOpen} />
            </section>
            <section class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
                <div class="flex items-start gap-4">
                    <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-accent">
                        <MaterialSymbolsTaskAltRounded class="size-6" />
                    </span>
                    <div class="flex min-w-0 flex-1 flex-col gap-1">
                        <h2 class="font-display text-xl font-semibold">Confirm before closing</h2>
                        <p class="text-sm text-mist-400">Ask for a second press before a ticket closes.</p>
                    </div>
                    <div class="shrink-0"><Toggle label="Confirm before closing" bind:checked={confirmClose} /></div>
                </div>
            </section>
        </div>
    </div>

    <SaveBar {dirty} onsave={() => settings.updateTickets({ guild, ...changes })} ondiscard={discard} />
</QueryGate>
