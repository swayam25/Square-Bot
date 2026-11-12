<script lang="ts">
    import JoinsChart from "#lib/components/JoinsChart.svelte";
    import NowPlayingBanner from "#lib/components/NowPlayingBanner.svelte";
    import PageHeading from "#lib/components/PageHeading.svelte";
    import SaveBar from "#lib/components/SaveBar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Toggle from "#lib/components/ui/Toggle.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { formatCount, plural } from "#lib/format.ts";
    import { MODULES, type ModuleKey } from "#lib/modules.ts";
    import * as settings from "#lib/settings.remote.ts";
    import { memberJoins, serverStats } from "#lib/stats.remote.ts";
    import MaterialSymbolsArrowForwardRounded from "~icons/material-symbols/arrow-forward-rounded";
    import MaterialSymbolsOpenInNewRounded from "~icons/material-symbols/open-in-new-rounded";
    import MaterialSymbolsPlayCircleRounded from "~icons/material-symbols/play-circle-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    const joinsQuery = $derived(data.guild.canManage ? memberJoins(data.guild.id) : null);
    const statsQuery = $derived(data.guild.canManage ? serverStats(data.guild.id) : null);
    const modulesQuery = $derived(data.guild.canManage ? settings.moduleSettings(data.guild.id) : null);

    const joins = $derived(joinsQuery?.current ?? null);
    const stats = $derived(statsQuery?.current ?? null);
    const modules = $derived(modulesQuery?.current ?? null);

    let drafts = $derived(modules ? { ...modules } : null);
    const moduleChanges = $derived(
        modules && drafts ? Object.fromEntries(MODULES.filter(({ key }) => drafts![key] !== modules[key]).map(({ key }) => [key, drafts![key]])) : {},
    );
    const toggle = (key: ModuleKey, on: boolean) => drafts && (drafts = { ...drafts, [key]: on });

    const joinedTotal = $derived(joins?.days.reduce((sum, day) => sum + day.count, 0) ?? 0);
    const since = (ms: number) => new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric" }).format(ms);
    const tiles = $derived(
        stats
            ? [
                  {
                      label: "Members",
                      value: formatCount(stats.humans + stats.bots),
                      detail: `${plural(stats.humans, "human")} · ${plural(stats.bots, "bot")}`,
                      dot: "bg-accent",
                  },
                  {
                      label: "In voice",
                      value: formatCount(stats.inVoice),
                      detail: stats.inVoice === 1 ? "person talking or listening" : "people talking or listening",
                      dot: "bg-emerald-400",
                  },
                  {
                      label: "Boosts",
                      value: formatCount(stats.boosts),
                      detail: stats.boostLevel ? `Level ${stats.boostLevel}` : "No boost level yet",
                      dot: "bg-pink-300",
                  },
                  {
                      label: "Channels",
                      value: formatCount(stats.textChannels + stats.voiceChannels),
                      detail: `${formatCount(stats.textChannels)} text · ${formatCount(stats.voiceChannels)} voice`,
                      dot: "bg-sky-300",
                  },
                  { label: "Roles", value: formatCount(stats.roles), detail: "Not counting @everyone", dot: "bg-violet-300" },
                  { label: "Created", value: since(stats.createdAt), detail: "When the server was made", dot: "bg-amber-400" },
              ]
            : [],
    );
</script>

{#snippet quickLinks()}
    <Button href="/guild/{data.guild.id}/player"><MaterialSymbolsPlayCircleRounded />Open the player</Button>
    <Button href="https://discord.com/channels/{data.guild.id}" target="_blank" rel="noopener noreferrer" variant="ghost">
        Open in Discord<MaterialSymbolsOpenInNewRounded />
    </Button>
{/snippet}

<div class="flex flex-col gap-8">
    <PageHeading title="Overview" description="What's happening in {data.guild.name} right now." actions={quickLinks} />

    {#if statsQuery}
        <section aria-label="Server stats" class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
            {#if stats}
                {#each tiles as tile (tile.label)}
                    <div class="flex min-w-0 flex-col gap-2 rounded-3xl bg-surface-1 p-4">
                        <span class="flex items-center gap-2 text-sm text-mist-400"
                            ><span class={["size-2 shrink-0 rounded-full", tile.dot]}></span>{tile.label}</span
                        >
                        <span class="truncate font-mono text-2xl font-semibold">{tile.value}</span>
                        <span class="truncate text-xs text-mist-400">{tile.detail}</span>
                    </div>
                {/each}
            {:else if statsQuery.error}
                <p class="col-span-full text-sm text-red-400">Square couldn't load the server stats. Refresh to try again.</p>
            {:else}
                {#each { length: 6 }, i (i)}<div aria-hidden="true" class="h-28 animate-pulse rounded-3xl bg-surface-1"></div>{/each}
            {/if}
        </section>
    {/if}

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
                        {joinedTotal ? `${plural(joinedTotal, "member")} joined in the last 30 days` : "Nobody joined in the last 30 days"}
                        · {plural(joins.members, "member")} now
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
