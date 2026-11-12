<script lang="ts">
    import JoinsChart from "#lib/components/JoinsChart.svelte";
    import NowPlayingBanner from "#lib/components/NowPlayingBanner.svelte";
    import PageHeading from "#lib/components/PageHeading.svelte";
    import SaveBar from "#lib/components/SaveBar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Toggle from "#lib/components/ui/Toggle.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { MODULES, type ModuleKey } from "#lib/modules.ts";
    import * as settings from "#lib/settings.remote.ts";
    import { memberJoins } from "#lib/stats.remote.ts";
    import MaterialSymbolsArrowForwardRounded from "~icons/material-symbols/arrow-forward-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    const joinsQuery = $derived(data.guild.canManage ? memberJoins(data.guild.id) : null);
    const modulesQuery = $derived(data.guild.canManage ? settings.moduleSettings(data.guild.id) : null);

    const joins = $derived(joinsQuery?.current ?? null);
    const modules = $derived(modulesQuery?.current ?? null);

    let drafts = $derived(modules ? { ...modules } : null);
    const moduleChanges = $derived(
        modules && drafts ? Object.fromEntries(MODULES.filter(({ key }) => drafts![key] !== modules[key]).map(({ key }) => [key, drafts![key]])) : {},
    );
    const toggle = (key: ModuleKey, on: boolean) => drafts && (drafts = { ...drafts, [key]: on });

    const joinedTotal = $derived(joins?.days.reduce((sum, day) => sum + day.count, 0) ?? 0);
    const count = (value: number, word: string) => `${value.toLocaleString("en-US")} ${word}${value === 1 ? "" : "s"}`;
</script>

<div class="flex flex-col gap-8">
    <PageHeading title="Overview" description="What's happening in {data.guild.name} right now." />

    {#if modules && drafts}
        <section aria-labelledby="modules" class="flex flex-col gap-4">
            <h2 id="modules" class="font-display text-xl font-semibold">Modules</h2>
            <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {#each MODULES as module (module.key)}
                    <div class="flex flex-col gap-4 rounded-4xl bg-surface-1 p-6">
                        <div class="flex items-start justify-between gap-4">
                            <span
                                class={[
                                    "flex size-12 shrink-0 items-center justify-center rounded-2xl transition-colors duration-200",
                                    drafts[module.key] ? "bg-accent/10 text-accent" : "bg-surface-2 text-mist-400",
                                ]}
                            >
                                <module.icon class="size-6" />
                            </span>
                            <Toggle label="{module.label} module" bind:checked={() => drafts![module.key], (on) => toggle(module.key, on)} />
                        </div>
                        <div class="flex flex-1 flex-col gap-1">
                            <h3 class="font-display text-lg font-semibold">{module.label}</h3>
                            <p class="text-sm text-mist-400">{module.description}</p>
                        </div>
                        {#if modules[module.key]}
                            <Button href="/guild/{data.guild.id}/{module.path}" class="self-start"
                                >Settings<MaterialSymbolsArrowForwardRounded /></Button
                            >
                        {:else}
                            <Tooltip content="Turn {module.label} on and save first" class="self-start">
                                <Button disabled>Settings<MaterialSymbolsArrowForwardRounded /></Button>
                            </Tooltip>
                        {/if}
                    </div>
                {/each}
            </div>
        </section>
    {:else if modulesQuery?.error}
        <p class="text-sm text-red-400">Square couldn't load the modules. Refresh to try again.</p>
    {:else if modulesQuery}
        <div aria-hidden="true" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {#each MODULES as module (module.key)}
                <div class="h-60 animate-pulse rounded-4xl bg-surface-1"></div>
            {/each}
        </div>
    {/if}

    <NowPlayingBanner guild={data.guild.id} />

    {#if joinsQuery}
        <section aria-labelledby="joins" class="flex flex-col gap-6 rounded-4xl bg-surface-1 p-6">
            <div class="flex flex-col gap-1">
                <h2 id="joins" class="font-display text-xl font-semibold">Member joins</h2>
                {#if joins}
                    <p class="text-sm text-mist-400">
                        {joinedTotal ? `${count(joinedTotal, "member")} joined in the last 30 days` : "Nobody joined in the last 30 days"}
                        · {count(joins.members, "member")} now
                    </p>
                {:else if joinsQuery.error}
                    <p class="text-sm text-red-400">Square couldn't load member joins. Refresh to try again.</p>
                {:else}
                    <div aria-hidden="true" class="h-5 w-64 animate-pulse rounded-full bg-surface-2"></div>
                {/if}
            </div>
            <div class="h-56">
                {#if joins}
                    <JoinsChart days={joins.days} />
                {:else if !joinsQuery.error}
                    <div aria-hidden="true" class="size-full animate-pulse rounded-2xl bg-surface-2"></div>
                {/if}
            </div>
        </section>
    {/if}
</div>

<SaveBar
    dirty={Object.keys(moduleChanges).length > 0}
    onsave={() => settings.updateModules({ guild: data.guild.id, ...moduleChanges })}
    ondiscard={() => (drafts = modules ? { ...modules } : null)}
/>
