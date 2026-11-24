<script lang="ts">
    import SettingGroup from "#lib/components/dashboard/SettingGroup.svelte";
    import Mention from "#lib/components/discord/Mention.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import type { SquarePermissions } from "#lib/permissions.ts";
    import type { Punishment } from "@square/api-client";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import MaterialSymbolsBlockRounded from "~icons/material-symbols/block-rounded";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";
    import MaterialSymbolsHourglassRounded from "~icons/material-symbols/hourglass-rounded";
    import MaterialSymbolsPersonRemoveRounded from "~icons/material-symbols/person-remove-rounded";
    import { DURATIONS, LIMITS } from "./automod.ts";

    let { steps = $bindable(), problems, perms }: { steps: Punishment[]; problems: Record<number, string>; perms: SquarePermissions } = $props();

    const ACTIONS = [
        { value: "timeout", label: "Timeout", icon: MaterialSymbolsHourglassRounded, permission: "ModerateMembers" },
        { value: "kick", label: "Kick", icon: MaterialSymbolsPersonRemoveRounded, permission: "KickMembers" },
        { value: "ban", label: "Ban", icon: MaterialSymbolsBlockRounded, permission: "BanMembers" },
    ] as const;
    const actionChoices = $derived(ACTIONS.map(({ permission, ...action }) => ({ ...action, disabled: perms.reason(permission) ?? undefined })));
    const usable = $derived(ACTIONS.find((action) => perms.has(action.permission))?.value);

    const full = $derived(steps.length >= LIMITS.punishments);

    function add() {
        if (!usable) return;
        const next = Math.min(Math.max(0, ...steps.map((step) => step.warnings ?? 0)) + 1, LIMITS.warnings);
        steps = [...steps, { warnings: next, action: usable, seconds: usable === "timeout" ? 3600 : null }];
    }

    function setAction(index: number, action: Punishment["action"]) {
        steps[index] = { ...steps[index]!, action, seconds: action === "timeout" ? (steps[index]!.seconds ?? 3600) : null };
    }
</script>

{#snippet commands()}
    Give warnings with <Mention kind="command" name="warn" /> and see them with <Mention kind="command" name="warnings" />. When someone reaches a
    count, Square runs that step. AutoMod rules set to warn count too.
{/snippet}

<SettingGroup title="Punishments">
    {#snippet actions()}
        <Tooltip
            content={full
                ? `Up to ${LIMITS.punishments} steps`
                : usable
                  ? null
                  : "Square needs the Timeout Members, Kick Members or Ban Members permission"}
        >
            <Button disabled={full || !usable} onclick={add}><MaterialSymbolsAddRounded />Add step</Button>
        </Tooltip>
    {/snippet}
    <p class="p-4 text-sm text-gray-400">{@render commands()}</p>
    {#each steps as step, index (index)}
        <div class="flex flex-wrap items-center gap-2 p-4">
            <span class="text-sm text-gray-400">At</span>
            <div class="w-32 shrink-0">
                <Input
                    type="number"
                    min={1}
                    max={LIMITS.warnings}
                    step={1}
                    aria-label="Warning count"
                    error={problems[index]}
                    bind:value={step.warnings}
                />
            </div>
            <span class="text-sm text-gray-400">warnings</span>
            <Select
                title="Punishment"
                options={actionChoices}
                class="w-40"
                bind:value={() => step.action, (next) => next && setAction(index, next as Punishment["action"])}
            />
            {#if step.action === "timeout"}
                <Select
                    title="Timeout length"
                    options={DURATIONS}
                    class="w-40"
                    bind:value={() => String(step.seconds ?? 3600), (next) => next && (step.seconds = Number(next))}
                />
            {/if}
            <Tooltip content="Remove step" class="ml-auto">
                <Button variant="ghost-danger" icon onclick={() => (steps = steps.filter((_, at) => at !== index))}>
                    <MaterialSymbolsCloseRounded />
                </Button>
            </Tooltip>
        </div>
    {:else}
        <p class="p-4 text-sm text-gray-400">No steps yet, so warnings are only kept on record.</p>
    {/each}
</SettingGroup>
