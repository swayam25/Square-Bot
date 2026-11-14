<script module lang="ts">
    import type { Series } from "#lib/components/DailyChart.svelte";
    import type { ActivityDay, JoinDay } from "@square/api-client";

    const JOINED: Series<JoinDay> = [{ key: "count", label: "Joined", color: "var(--color-accent)" }];
    const TICKETS: Series<ActivityDay> = [
        { key: "ticketsOpened", label: "Opened", color: "var(--color-accent)" },
        { key: "ticketsClosed", label: "Closed", color: "var(--color-violet-300)" },
    ];
    const INVITES: Series<ActivityDay> = [
        { key: "invited", label: "Invited", color: "var(--color-emerald-400)" },
        { key: "left", label: "Left", color: "var(--color-red-400)" },
    ];
</script>

<script lang="ts">
    import DailyChart from "#lib/components/DailyChart.svelte";
    import NowPlayingBanner from "#lib/components/NowPlayingBanner.svelte";
    import PageHeading from "#lib/components/PageHeading.svelte";
    import SaveBar from "#lib/components/SaveBar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import Toggle from "#lib/components/ui/Toggle.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { formatCount, monthYear, plural } from "#lib/format.ts";
    import { MODULES, type ModuleKey } from "#lib/modules.ts";
    import * as settings from "#lib/settings.remote.ts";
    import { activity, memberJoins, serverStats } from "#lib/stats.remote.ts";
    import type { Snippet } from "svelte";
    import MaterialSymbolsArrowForwardRounded from "~icons/material-symbols/arrow-forward-rounded";
    import MaterialSymbolsCakeRounded from "~icons/material-symbols/cake-rounded";
    import MaterialSymbolsGroupRounded from "~icons/material-symbols/group-rounded";
    import MaterialSymbolsHeadphonesRounded from "~icons/material-symbols/headphones-rounded";
    import MaterialSymbolsOpenInNewRounded from "~icons/material-symbols/open-in-new-rounded";
    import MaterialSymbolsPlayCircleRounded from "~icons/material-symbols/play-circle-rounded";
    import MaterialSymbolsRocketLaunchRounded from "~icons/material-symbols/rocket-launch-rounded";
    import MaterialSymbolsShieldPersonRounded from "~icons/material-symbols/shield-person-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    const joinsQuery = $derived(data.guild.canManage ? memberJoins(data.guild.id) : null);
    const statsQuery = $derived(data.guild.canManage ? serverStats(data.guild.id) : null);
    const modulesQuery = $derived(data.guild.canManage ? settings.moduleSettings(data.guild.id) : null);

    const activityQuery = $derived(data.guild.canManage ? activity(data.guild.id) : null);
    const joins = $derived(joinsQuery?.current ?? null);
    const days = $derived(activityQuery?.current?.days ?? null);
    const total = (key: keyof Omit<ActivityDay, "date">) => days?.reduce((sum, day) => sum + day[key], 0) ?? 0;
    const stats = $derived(statsQuery?.current ?? null);
    const modules = $derived(modulesQuery?.current ?? null);

    let drafts = $derived(modules ? { ...modules } : null);
    const moduleChanges = $derived(
        modules && drafts ? Object.fromEntries(MODULES.filter(({ key }) => drafts![key] !== modules[key]).map(({ key }) => [key, drafts![key]])) : {},
    );
    const toggle = (key: ModuleKey, on: boolean) => drafts && (drafts = { ...drafts, [key]: on });

    const joinedTotal = $derived(joins?.days.reduce((sum, day) => sum + day.count, 0) ?? 0);
    const since = (ms: number) => monthYear.format(ms);
    const tiles = $derived(
        stats
            ? [
                  {
                      label: "Members",
                      value: formatCount(stats.humans + stats.bots),
                      detail: `${plural(stats.humans, "human")} · ${plural(stats.bots, "bot")}`,
                      icon: MaterialSymbolsGroupRounded,
                      tone: "text-accent",
                  },
                  {
                      label: "In voice",
                      value: formatCount(stats.inVoice),
                      detail: stats.inVoice === 1 ? "person talking or listening" : "people talking or listening",
                      icon: MaterialSymbolsHeadphonesRounded,
                      tone: "text-emerald-400",
                  },
                  {
                      label: "Boosts",
                      value: formatCount(stats.boosts),
                      detail: stats.boostLevel ? `Level ${stats.boostLevel}` : "No boost level yet",
                      icon: MaterialSymbolsRocketLaunchRounded,
                      tone: "text-pink-300",
                  },
                  {
                      label: "Channels",
                      value: formatCount(stats.textChannels + stats.voiceChannels),
                      detail: `${formatCount(stats.textChannels)} text · ${formatCount(stats.voiceChannels)} voice`,
                      icon: MaterialSymbolsTagRounded,
                      tone: "text-sky-300",
                  },
                  {
                      label: "Roles",
                      value: formatCount(stats.roles),
                      detail: "Not counting @everyone",
                      icon: MaterialSymbolsShieldPersonRounded,
                      tone: "text-violet-300",
                  },
                  {
                      label: "Created",
                      value: since(stats.createdAt),
                      detail: "When the server was made",
                      icon: MaterialSymbolsCakeRounded,
                      tone: "text-amber-400",
                  },
              ]
            : [],
    );
</script>

{#snippet activityCard(id: string, title: string, summary: Snippet, series: Series<ActivityDay>)}
    <section aria-labelledby={id} class="flex flex-col gap-4 rounded-3xl bg-surface-1 p-4">
        <div class="flex flex-col gap-1">
            <h2 {id} class="font-display text-xl font-semibold">{title}</h2>
            {#if days}
                <p class="text-sm text-gray-400">{@render summary()}</p>
            {:else if !activityQuery?.error}
                <span aria-hidden="true" class="flex h-5 items-center"><span class="h-4 w-64 skeleton rounded-full"></span></span>
            {/if}
        </div>
        <div class="h-48">
            {#if days}
                <DailyChart {days} {series} />
            {:else if activityQuery?.error}
                <EmptyState
                    tone="danger"
                    compact
                    class="size-full"
                    title="Couldn't load {title.toLowerCase()}"
                    text={activityQuery.error.message ?? "Square didn't answer. Try again in a moment."}
                    retry={() => activityQuery.refresh()}
                />
            {:else}
                <div aria-hidden="true" class="size-full skeleton rounded-2xl"></div>
            {/if}
        </div>
    </section>
{/snippet}

{#snippet quickLinks()}
    <Button href="/guild/{data.guild.id}/player"><MaterialSymbolsPlayCircleRounded />Open the player</Button>
    <Button href="https://discord.com/channels/{data.guild.id}" target="_blank" rel="noopener noreferrer" variant="ghost">
        Open in Discord<MaterialSymbolsOpenInNewRounded />
    </Button>
{/snippet}

<div class="flex flex-col gap-6">
    <PageHeading title="Overview" description="What's happening in {data.guild.name} right now." actions={quickLinks} />

    {#if statsQuery}
        <section aria-label="Server stats" class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
            {#if stats}
                {#each tiles as tile (tile.label)}
                    <div class="flex min-w-0 flex-col gap-2 rounded-3xl bg-surface-1 p-4">
                        <span class="flex items-center gap-2 text-sm text-gray-400"
                            ><tile.icon class={["size-5 shrink-0", tile.tone]} />{tile.label}</span
                        >
                        <span class="truncate font-mono text-2xl font-semibold">{tile.value}</span>
                        <span class="truncate text-xs text-gray-400">{tile.detail}</span>
                    </div>
                {/each}
            {:else if statsQuery.error}
                <EmptyState
                    tone="danger"
                    card
                    compact
                    class="col-span-full"
                    title="Couldn't load the server stats"
                    text={statsQuery.error.message ?? "Square didn't answer. Try again in a moment."}
                    retry={() => statsQuery.refresh()}
                />
            {:else}
                {#each { length: 6 }, i (i)}
                    <div aria-hidden="true" class="flex flex-col gap-2 rounded-3xl bg-surface-1 p-4">
                        <span class="flex h-5 items-center gap-2"
                            ><span class="size-5 skeleton rounded-full"></span><span class="h-4 w-16 skeleton rounded-full"></span></span
                        >
                        <span class="flex h-8 items-center"><span class="h-6 w-12 skeleton rounded-full"></span></span>
                        <span class="flex h-4 items-center"><span class="h-2 w-24 skeleton rounded-full"></span></span>
                    </div>
                {/each}
            {/if}
        </section>
    {/if}

    {#if modules && drafts}
        <section aria-labelledby="modules" class="flex flex-col gap-4">
            <h2 id="modules" class="font-display text-xl font-semibold">Modules</h2>
            <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {#each MODULES as module (module.key)}
                    <div class="flex flex-col gap-4 rounded-3xl bg-surface-1 p-4">
                        <div class="flex items-start justify-between gap-4">
                            <span
                                class={[
                                    "flex size-12 shrink-0 items-center justify-center rounded-2xl transition-colors duration-200",
                                    drafts[module.key] ? "bg-accent/10 text-accent" : "bg-surface-2 text-gray-400",
                                ]}
                            >
                                <module.icon class="size-6" />
                            </span>
                            <Toggle label="{module.label} module" bind:checked={() => drafts![module.key], (on) => toggle(module.key, on)} />
                        </div>
                        <div class="flex flex-1 flex-col gap-1">
                            <h3 class="font-display text-lg font-semibold">{module.label}</h3>
                            <p class="text-sm text-gray-400">{module.description}</p>
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
        <EmptyState
            tone="danger"
            card
            title="Couldn't load the modules"
            text={modulesQuery.error.message ?? "Square didn't answer. Try again in a moment."}
            retry={() => modulesQuery.refresh()}
        />
    {:else if modulesQuery}
        <div aria-hidden="true" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {#each MODULES as module (module.key)}
                <div class="flex flex-col gap-4 rounded-3xl bg-surface-1 p-4">
                    <div class="flex items-start justify-between gap-4">
                        <span class="size-12 skeleton rounded-2xl"></span>
                        <span class="h-8 w-14 skeleton rounded-full"></span>
                    </div>
                    <div class="flex flex-1 flex-col gap-2">
                        <span class="h-5 w-24 skeleton rounded-full"></span>
                        <span class="h-4 w-4/5 skeleton rounded-full"></span>
                    </div>
                    <span class="h-12 w-28 skeleton rounded-full md:h-10"></span>
                </div>
            {/each}
        </div>
    {/if}

    <NowPlayingBanner guild={data.guild.id} />

    {#if joinsQuery}
        <section aria-labelledby="joins" class="flex flex-col gap-4 rounded-3xl bg-surface-1 p-4">
            <div class="flex flex-col gap-1">
                <h2 id="joins" class="font-display text-xl font-semibold">Member joins</h2>
                {#if joins}
                    <p class="text-sm text-gray-400">
                        {joinedTotal ? `${plural(joinedTotal, "member")} joined in the last 30 days` : "Nobody joined in the last 30 days"}
                        · {plural(joins.members, "member")} now
                    </p>
                {:else if !joinsQuery.error}
                    <div aria-hidden="true" class="h-5 w-64 skeleton rounded-full"></div>
                {/if}
            </div>
            <div class="h-56">
                {#if joins}
                    <DailyChart days={joins.days} series={JOINED} />
                {:else if joinsQuery.error}
                    <EmptyState
                        tone="danger"
                        compact
                        class="size-full"
                        title="Couldn't load member joins"
                        text={joinsQuery.error.message ?? "Square didn't answer. Try again in a moment."}
                        retry={() => joinsQuery.refresh()}
                    />
                {:else}
                    <div aria-hidden="true" class="size-full skeleton rounded-2xl"></div>
                {/if}
            </div>
        </section>
    {/if}

    {#if activityQuery && modules && (modules.tickets || modules.invites)}
        <div class="grid gap-6 xl:grid-cols-2">
            {#if modules.tickets}
                {#snippet tickets()}
                    {#if total("ticketsOpened") || total("ticketsClosed")}
                        <span class="text-accent">{formatCount(total("ticketsOpened"))} opened</span> ·
                        <span class="text-violet-300">{formatCount(total("ticketsClosed"))} closed</span> in the last 30 days
                    {:else}
                        No tickets opened or closed in the last 30 days
                    {/if}
                {/snippet}
                {@render activityCard("tickets-chart", "Tickets", tickets, TICKETS)}
            {/if}
            {#if modules.invites}
                {#snippet invites()}
                    {#if total("invited") || total("left")}
                        <span class="text-emerald-400">{plural(total("invited"), "member")} invited</span> ·
                        <span class="text-red-400">{formatCount(total("left"))} left</span> in the last 30 days
                    {:else}
                        Nobody joined through an invite in the last 30 days
                    {/if}
                {/snippet}
                {@render activityCard("invites-chart", "Invites", invites, INVITES)}
            {/if}
        </div>
    {/if}
</div>

<SaveBar
    dirty={Object.keys(moduleChanges).length > 0}
    onsave={() => settings.updateModules({ guild: data.guild.id, ...moduleChanges })}
    ondiscard={() => (drafts = modules ? { ...modules } : null)}
/>
