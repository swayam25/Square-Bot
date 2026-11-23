<script lang="ts">
    import { edgeFade } from "#lib/attachments/edge-fade.ts";
    import { ripple } from "#lib/attachments/ripple.ts";
    import { Details, setDetails } from "#lib/components/dashboard/details.svelte.ts";
    import AccountMenu from "#lib/components/site/AccountMenu.svelte";
    import Island from "#lib/components/site/Island.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Drawer from "#lib/components/ui/Drawer.svelte";
    import GuildIcon from "#lib/components/ui/GuildIcon.svelte";
    import OverlayScrollbar from "#lib/components/ui/OverlayScrollbar.svelte";
    import Popup from "#lib/components/ui/Popup.svelte";
    import { focusRing, menuRow } from "#lib/components/ui/styles.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { guildEmojis } from "#lib/emoji/emoji.remote.ts";
    import { plural } from "#lib/format.ts";
    import { mobile } from "#lib/media.ts";
    import { refetch } from "#lib/refetch.ts";
    import { MODULES, type ModuleKey } from "#lib/settings/modules.ts";
    import { botPermissions, guildChannels, guildRoles, moduleSettings } from "#lib/settings/settings.remote.ts";
    import { load, save } from "#lib/storage.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { afterNavigate } from "$app/navigation";
    import { page } from "$app/state";
    import { onMount } from "svelte";
    import MaterialSymbolsCheckRounded from "~icons/material-symbols/check-rounded";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";
    import MaterialSymbolsDashboardRounded from "~icons/material-symbols/dashboard-rounded";
    import MaterialSymbolsEditSquareRounded from "~icons/material-symbols/edit-square-rounded";
    import MaterialSymbolsFormatPaintRounded from "~icons/material-symbols/format-paint-rounded";
    import MaterialSymbolsHomeRounded from "~icons/material-symbols/home-rounded";
    import MaterialSymbolsMusicNoteRounded from "~icons/material-symbols/music-note-rounded";
    import MaterialSymbolsPlayCircleRounded from "~icons/material-symbols/play-circle-rounded";
    import MaterialSymbolsPlayShapesRounded from "~icons/material-symbols/play-shapes-rounded";
    import MaterialSymbolsRefreshRounded from "~icons/material-symbols/refresh-rounded";
    import MaterialSymbolsShieldRounded from "~icons/material-symbols/shield-rounded";
    import MaterialSymbolsTuneRounded from "~icons/material-symbols/tune-rounded";
    import MaterialSymbolsUnfoldMoreRounded from "~icons/material-symbols/unfold-more-rounded";
    import MaterialSymbolsWarningRounded from "~icons/material-symbols/warning-rounded";
    import SvgSpinners90RingWithBg from "~icons/svg-spinners/90-ring-with-bg";
    import type { LayoutProps } from "./$types";

    let { data, children }: LayoutProps = $props();

    const SIDEBAR = { min: 88, max: 260 };
    const STORAGE_KEY = "square:sidebar";

    let width = $state(SIDEBAR.max);
    const expanded = $derived(width > 120);

    onMount(() => {
        const saved = Number(load(STORAGE_KEY));
        if (saved) width = Math.min(Math.max(saved, SIDEBAR.min), SIDEBAR.max);
    });

    const DETAILS = { min: 280, initial: 360, maxShare: 0.45 };
    const details = setDetails(new Details());
    let detailsWidth = $state(DETAILS.initial);
    const detailsOpen = $derived(details.content !== null);

    const clamp = (value: number, min: number, max: number) => Math.round(Math.min(Math.max(value, min), max));

    function drag(event: PointerEvent, move: (x: number) => void, done?: () => void) {
        if (event.button !== 0) return;
        event.preventDefault();
        const handle = event.currentTarget as HTMLElement;
        handle.setPointerCapture(event.pointerId);
        const onMove = (e: PointerEvent) => move(e.clientX);
        handle.addEventListener("pointermove", onMove);
        handle.addEventListener(
            "lostpointercapture",
            () => {
                handle.removeEventListener("pointermove", onMove);
                done?.();
            },
            { once: true },
        );
    }

    const resizeSidebar = (event: PointerEvent) =>
        drag(
            event,
            (x) => (width = clamp(x - 8, SIDEBAR.min, SIDEBAR.max)),
            () => save(STORAGE_KEY, String(width)),
        );
    const resizeDetails = (event: PointerEvent) =>
        drag(event, (x) => (detailsWidth = clamp(innerWidth - x - 8, DETAILS.min, innerWidth * DETAILS.maxShare)));

    const modulesQuery = $derived(data.guild.canManage ? moduleSettings(data.guild.id) : null);
    const modules = $derived(modulesQuery?.current ?? null);
    const moduleLink = (key: ModuleKey) => {
        const module = MODULES.find((module) => module.key === key)!;
        return { href: `${base}/${module.path}`, label: module.label, icon: module.icon, off: modules ? !modules[key] : false };
    };

    const base = $derived(`/guild/${data.guild.id}`);
    type Item = { href: string; label: string; icon: typeof MaterialSymbolsTuneRounded; off?: boolean };
    const groups: { label: string; items: Item[] }[] = $derived([
        {
            label: "",
            items: [
                { href: base, label: "Overview", icon: MaterialSymbolsDashboardRounded },
                { href: `${base}/player`, label: "Player", icon: MaterialSymbolsPlayCircleRounded },
            ],
        },
        ...(data.guild.canManage
            ? [
                  {
                      label: "Community",
                      items: [
                          { href: `${base}/music`, label: "Music", icon: MaterialSymbolsMusicNoteRounded },
                          moduleLink("invites"),
                          moduleLink("tickets"),
                          moduleLink("giveaways"),
                          moduleLink("starboard"),
                      ],
                  },
              ]
            : []),
        ...(data.guild.canManage
            ? [
                  {
                      label: "Server",
                      items: [
                          moduleLink("logs"),
                          { href: `${base}/automod`, label: "AutoMod", icon: MaterialSymbolsShieldRounded },
                          { href: `${base}/warnings`, label: "Warnings", icon: MaterialSymbolsWarningRounded },
                          moduleLink("autorole"),
                          { href: `${base}/customize`, label: "Customize", icon: MaterialSymbolsFormatPaintRounded },
                          { href: `${base}/composer`, label: "Composer", icon: MaterialSymbolsEditSquareRounded },
                      ],
                  },
              ]
            : []),
    ]);

    const section = $derived(page.url.pathname.slice(base.length));
    const isCurrent = (href: string) => (href === base ? page.url.pathname === base : page.url.pathname.startsWith(href));
    const switchHref = (guild: (typeof data.guilds)[number]) => `/guild/${guild.id}${guild.canManage ? section : ""}`;

    let switcherOpen = $state(false);
    let mobileSwitcherOpen = $state(false);
    let accountOpen = $state(false);
    let mobileAccountOpen = $state(false);
    const closeSwitcher = () => (switcherOpen = mobileSwitcherOpen = false);
    let scroller = $state<HTMLElement | null>(null);
    let detailsScroller = $state<HTMLElement | null>(null);
    const serverLists = $state<Record<"sidebar" | "nav", HTMLElement | null>>({ sidebar: null, nav: null });

    afterNavigate(({ from, to }) => {
        switcherOpen = mobileSwitcherOpen = accountOpen = mobileAccountOpen = false;
        if (from?.url.pathname === to?.url.pathname) return;
        details.close();
        scroller?.scrollTo({ top: 0, behavior: "instant" });
    });

    let refreshing = $state(false);
    async function refreshServer() {
        refreshing = true;
        try {
            await Promise.all([
                guildChannels(data.guild.id).refresh(),
                guildRoles(data.guild.id).refresh(),
                botPermissions(data.guild.id).refresh(),
                refetch(() => guildEmojis(data.guild.id)),
            ]);
            toast.success("Server synced");
        } catch {
            toast.error("Square couldn't sync the server. Try again.");
        } finally {
            refreshing = false;
        }
    }

    const stacked = "h-14 flex-col justify-center gap-0.5 rounded-3xl text-2xs";
</script>

{#snippet servers(spot: "sidebar" | "nav")}
    <div class="relative">
        <nav
            bind:this={serverLists[spot]}
            aria-label="Servers"
            class={[
                "flex flex-col gap-1",
                mobile.current ? "-m-1 p-1" : "-my-1 -mr-2 -ml-1 max-h-96 overflow-y-auto overscroll-contain py-1 pr-2 pl-1",
            ]}
        >
            {#each data.guilds as guild (guild.id)}
                <a
                    href={switchHref(guild)}
                    aria-current={guild.id === data.guild.id ? "page" : undefined}
                    class="ripple flex h-12 shrink-0 items-center gap-4 rounded-control-lg px-2 text-sm font-medium hover:bg-white/10 aria-[current=page]:text-accent"
                    {@attach ripple}
                    onclick={closeSwitcher}
                >
                    <GuildIcon src={guild.iconUrl} name={guild.name} class="size-8 rounded-xl text-gray-100" />
                    <span class="min-w-0 flex-1 truncate">{guild.name}</span>
                    {#if guild.id === data.guild.id}<MaterialSymbolsCheckRounded class="size-5 shrink-0" />{/if}
                </a>
            {/each}
        </nav>
        <OverlayScrollbar viewport={serverLists[spot]} />
    </div>
    <hr class="my-2 border-white/10" />
    <a
        href="/guild"
        class="ripple flex h-12 items-center gap-4 rounded-control-lg px-4 text-sm font-medium hover:bg-white/10"
        {@attach ripple}
        onclick={closeSwitcher}
    >
        <MaterialSymbolsPlayShapesRounded class="size-5 text-gray-400" />All servers
    </a>
{/snippet}

{#snippet refreshIcon()}
    {#if refreshing}
        <SvgSpinners90RingWithBg class="size-5 shrink-0 text-gray-400" />
    {:else}
        <MaterialSymbolsRefreshRounded class="size-5 shrink-0 text-gray-400" />
    {/if}
{/snippet}

{#snippet accountMenu()}
    {#if data.user}
        <AccountMenu user={data.user}>
            <a href="/" class={menuRow} {@attach ripple}><MaterialSymbolsHomeRounded />Home</a>
            {#if data.guild.canManage && mobile.current}
                <button disabled={refreshing} aria-busy={refreshing} class={menuRow} {@attach ripple} onclick={refreshServer}>
                    {@render refreshIcon()}{refreshing ? "Syncing…" : "Sync server"}
                </button>
            {/if}
        </AccountMenu>
    {/if}
{/snippet}

{#snippet link(item: Item, row: boolean)}
    {#if item.off}
        <Tooltip content="{item.label} is turned off. Turn it on from Overview." placement={mobile.current ? "top" : "right"} class="w-full">
            <span
                aria-disabled="true"
                class={[
                    "flex w-full shrink-0 cursor-not-allowed items-center font-medium text-gray-400 opacity-40",
                    row ? "h-10 gap-2 rounded-2xl px-3 text-sm" : stacked,
                ]}
            >
                <item.icon class="size-6 shrink-0" />
                <span class="max-w-full truncate">{item.label}</span>
            </span>
        </Tooltip>
    {:else}
        <a
            href={item.href}
            aria-current={isCurrent(item.href) ? "page" : undefined}
            class={[
                "ripple flex shrink-0 items-center font-medium text-gray-400 hover:bg-white/10 hover:text-gray-100 aria-[current=page]:bg-accent/10 aria-[current=page]:text-accent",
                row ? "h-10 gap-2 rounded-2xl px-3 text-sm" : [stacked, "w-full"],
                focusRing,
            ]}
            {@attach ripple}
        >
            <item.icon class="size-6 shrink-0" />
            <span class="max-w-full truncate">{item.label}</span>
        </a>
    {/if}
{/snippet}

<div
    style:--sidebar="{width}px"
    style:--details={detailsOpen ? `${detailsWidth + 8}px` : "0px"}
    class="flex h-dvh flex-col overflow-hidden bg-gray-900 md:flex-row md:p-2"
>
    <aside class="hidden w-(--sidebar) shrink-0 flex-col gap-4 overflow-hidden py-2 md:flex">
        <div class={["flex flex-col gap-4", expanded ? "px-4" : "items-center px-2"]}>
            <Popup
                bind:open={switcherOpen}
                title="Switch server"
                placement={expanded ? "bottom-start" : "right-start"}
                contentClass={expanded ? "w-(--reference-width)" : "w-72"}
                triggerClass={[
                    "ripple flex items-center text-left",
                    expanded ? "w-full gap-4 rounded-control-lg bg-gray-800 p-2 pr-4 hover:bg-gray-700" : "rounded-control-lg",
                    focusRing,
                ]}
            >
                {#snippet trigger()}
                    <GuildIcon
                        src={data.guild.iconUrl}
                        name={data.guild.name}
                        class={expanded ? "size-10 rounded-xl" : "size-12 rounded-control-lg"}
                    />
                    {#if expanded}
                        <span class="flex min-w-0 flex-1 flex-col">
                            <span class="truncate text-sm font-semibold">{data.guild.name}</span>
                            <span class="font-mono text-xs text-gray-400">{plural(data.guild.memberCount, "member")}</span>
                        </span>
                        <MaterialSymbolsUnfoldMoreRounded class="size-5 shrink-0 text-gray-400" />
                    {/if}
                {/snippet}
                {@render servers("sidebar")}
            </Popup>
        </div>

        <nav
            aria-label="Dashboard"
            class={["edge-fade-y flex min-h-0 flex-1 scrollbar-none flex-col gap-6 overflow-y-auto py-2", expanded ? "px-4" : "px-2"]}
            {@attach edgeFade("y")}
        >
            {#each groups as group, index (index)}
                <div class="flex flex-col gap-1">
                    {#if expanded && group.label}
                        <div class="flex items-center gap-2 px-4 pb-1">
                            <span class="font-mono text-2xs font-semibold tracking-wider text-gray-400 uppercase">{group.label}</span>
                            <span class="h-px flex-1 bg-white/10"></span>
                        </div>
                    {:else if !expanded && index > 0}
                        <span class="mx-auto mb-2 h-px w-8 bg-white/10"></span>
                    {/if}
                    {#each group.items as item (item.href)}
                        {@render link(item, expanded)}
                    {/each}
                </div>
            {/each}
        </nav>

        {#if data.guild.canManage}
            <div class={expanded ? "px-4" : "flex justify-center px-2"}>
                <Tooltip
                    content="Get the latest server info from Discord"
                    placement={expanded ? "top" : "right"}
                    class={expanded ? "w-full" : undefined}
                >
                    <button
                        disabled={refreshing}
                        aria-busy={refreshing}
                        class={[
                            "ripple flex items-center gap-4 text-sm font-medium text-gray-400 hover:bg-gray-800 hover:text-gray-100",
                            expanded ? "h-10 w-full rounded-2xl px-3" : "size-12 justify-center rounded-control-lg",
                            focusRing,
                        ]}
                        {@attach ripple}
                        onclick={refreshServer}
                    >
                        {@render refreshIcon()}
                        {#if expanded}<span class="truncate">{refreshing ? "Syncing…" : "Sync server"}</span>{/if}
                    </button>
                </Tooltip>
            </div>
        {/if}

        {#if data.user}
            <div class={expanded ? "px-4" : "flex justify-center px-2"}>
                <Popup
                    bind:open={accountOpen}
                    title="Your account"
                    placement={expanded ? "top-start" : "right-end"}
                    triggerClass={[
                        "ripple flex items-center gap-4 rounded-control-lg text-left hover:bg-gray-800",
                        expanded ? "w-full p-2 pr-4" : "p-2",
                        focusRing,
                    ]}
                >
                    {#snippet trigger()}
                        <Avatar src={data.user!.avatarUrl} name={data.user!.name} class="size-10" />
                        {#if expanded}
                            <span class="flex min-w-0 flex-1 flex-col">
                                <span class="truncate text-sm font-semibold">{data.user!.name}</span>
                                <span class="truncate font-mono text-xs text-gray-400">@{data.user!.username}</span>
                            </span>
                        {/if}
                    {/snippet}
                    {@render accountMenu()}
                </Popup>
            </div>
        {/if}
    </aside>

    <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize sidebar"
        aria-valuemin={SIDEBAR.min}
        aria-valuemax={SIDEBAR.max}
        aria-valuenow={width}
        class="group hidden w-2 shrink-0 cursor-col-resize justify-center md:flex"
        onpointerdown={resizeSidebar}
    >
        <span class="h-full w-1 rounded-full transition-colors duration-200 group-hover:bg-gray-400 group-active:bg-gray-400"></span>
    </div>

    <div class="relative min-h-0 min-w-0 flex-1 animate-shell-in overflow-hidden rounded-b-card bg-gray-950 md:rounded-card">
        <main bind:this={scroller} class="size-full overflow-y-auto overscroll-contain px-4 py-6 md:px-8">
            {#key page.url.pathname}
                <div class="animate-page-in">{@render children()}</div>
            {/key}
        </main>
        <OverlayScrollbar viewport={scroller} inset={24} />
        <Island docked />
    </div>

    {#if details.content}
        {#if mobile.current}
            <Drawer bind:open={() => detailsOpen, (open) => !open && details.close()} title={details.title}>
                {@render details.content()}
            </Drawer>
        {:else}
            <div
                role="separator"
                aria-orientation="vertical"
                aria-label="Resize panel"
                aria-valuemin={DETAILS.min}
                aria-valuenow={detailsWidth}
                class="group flex w-2 shrink-0 cursor-col-resize justify-center"
                onpointerdown={resizeDetails}
            >
                <span class="h-full w-1 rounded-full transition-colors duration-200 group-hover:bg-gray-400 group-active:bg-gray-400"></span>
            </div>
            <!-- Reaches over the shell padding so its scrollbar sits at the window edge -->
            <aside aria-label={details.title} class="-mr-2 flex w-(--details) shrink-0 flex-col">
                {#key details.key}
                    <div class="flex min-h-0 flex-1 animate-panel-in flex-col">
                        <div class="flex items-center gap-4 py-2 pr-4 pl-4">
                            <h2 class="min-w-0 flex-1 truncate font-display text-xl font-semibold">{details.title}</h2>
                            <Tooltip content="Close panel">
                                <Button variant="ghost" icon onclick={() => details.close()}><MaterialSymbolsCloseRounded /></Button>
                            </Tooltip>
                        </div>
                        <div class="relative min-h-0 flex-1">
                            <div bind:this={detailsScroller} class="size-full overflow-y-auto overscroll-contain p-4">
                                {@render details.content()}
                            </div>
                            <OverlayScrollbar viewport={detailsScroller} />
                        </div>
                    </div>
                {/key}
            </aside>
        {/if}
    {/if}

    <nav aria-label="Dashboard" class="shrink-0 pt-1 pb-[calc(0.25rem+env(safe-area-inset-bottom))] md:hidden">
        <div class="edge-fade-x flex scrollbar-none overflow-x-auto" {@attach edgeFade("x")}>
            <div class="flex w-max min-w-full items-center justify-evenly gap-2 px-4 py-1">
                <Popup
                    bind:open={mobileSwitcherOpen}
                    title="Switch server"
                    triggerClass={["ripple flex w-16 shrink-0 items-center", stacked, focusRing]}
                >
                    {#snippet trigger()}
                        <GuildIcon src={data.guild.iconUrl} name={data.guild.name} class="size-6 rounded-lg" />
                        <span class="max-w-full truncate font-medium text-gray-400">Server</span>
                    {/snippet}
                    {@render servers("nav")}
                </Popup>
                {#each groups as group, index (index)}
                    <span class="h-8 w-px shrink-0 bg-white/10"></span>
                    {#each group.items as item (item.href)}
                        <div class="w-16 shrink-0">{@render link(item, false)}</div>
                    {/each}
                {/each}
                {#if data.user}
                    <span class="h-8 w-px shrink-0 bg-white/10"></span>
                    <Popup
                        bind:open={mobileAccountOpen}
                        title="Your account"
                        triggerClass={["ripple flex w-16 shrink-0 items-center", stacked, focusRing]}
                    >
                        {#snippet trigger()}
                            <Avatar src={data.user!.avatarUrl} name={data.user!.name} class="size-6" />
                            <span class="max-w-full truncate font-medium text-gray-400">You</span>
                        {/snippet}
                        {@render accountMenu()}
                    </Popup>
                {/if}
            </div>
        </div>
    </nav>
</div>
