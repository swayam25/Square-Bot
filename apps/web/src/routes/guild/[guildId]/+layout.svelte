<script lang="ts">
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Drawer from "#lib/components/ui/Drawer.svelte";
    import GuildIcon from "#lib/components/ui/GuildIcon.svelte";
    import Popup from "#lib/components/ui/Popup.svelte";
    import { Details, setDetails } from "#lib/details.svelte.ts";
    import { mobile } from "#lib/media.ts";
    import { ripple } from "#lib/motion.ts";
    import { load, save } from "#lib/storage.ts";
    import { afterNavigate } from "$app/navigation";
    import { page } from "$app/state";
    import { onMount } from "svelte";
    import MaterialSymbolsCheckRounded from "~icons/material-symbols/check-rounded";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";
    import MaterialSymbolsConfirmationNumberRounded from "~icons/material-symbols/confirmation-number-rounded";
    import MaterialSymbolsDashboardRounded from "~icons/material-symbols/dashboard-rounded";
    import MaterialSymbolsDescriptionRounded from "~icons/material-symbols/description-rounded";
    import MaterialSymbolsGridViewRounded from "~icons/material-symbols/grid-view-rounded";
    import MaterialSymbolsHomeRounded from "~icons/material-symbols/home-rounded";
    import MaterialSymbolsLogoutRounded from "~icons/material-symbols/logout-rounded";
    import MaterialSymbolsMusicNoteRounded from "~icons/material-symbols/music-note-rounded";
    import MaterialSymbolsPersonAddRounded from "~icons/material-symbols/person-add-rounded";
    import MaterialSymbolsTuneRounded from "~icons/material-symbols/tune-rounded";
    import MaterialSymbolsUnfoldMoreRounded from "~icons/material-symbols/unfold-more-rounded";
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
            (x) => (width = clamp(x, SIDEBAR.min, SIDEBAR.max)),
            () => save(STORAGE_KEY, String(width)),
        );
    const resizeDetails = (event: PointerEvent) =>
        drag(event, (x) => (detailsWidth = clamp(innerWidth - x - 8, DETAILS.min, innerWidth * DETAILS.maxShare)));

    const base = $derived(`/guild/${data.guild.id}`);
    const groups = $derived([
        { label: "", items: [{ href: base, label: "Overview", icon: MaterialSymbolsDashboardRounded }] },
        {
            label: "Community",
            items: [
                { href: `${base}/music`, label: "Music", icon: MaterialSymbolsMusicNoteRounded },
                ...(data.guild.canManage
                    ? [
                          { href: `${base}/invites`, label: "Invites", icon: MaterialSymbolsPersonAddRounded },
                          { href: `${base}/tickets`, label: "Tickets", icon: MaterialSymbolsConfirmationNumberRounded },
                      ]
                    : []),
            ],
        },
        ...(data.guild.canManage
            ? [
                  {
                      label: "Server",
                      items: [
                          { href: `${base}/logs`, label: "Logs", icon: MaterialSymbolsDescriptionRounded },
                          { href: `${base}/general`, label: "General", icon: MaterialSymbolsTuneRounded },
                      ],
                  },
              ]
            : []),
    ]);

    const section = $derived(page.url.pathname.slice(base.length));
    const isCurrent = (href: string) => (href === base ? page.url.pathname === base : page.url.pathname.startsWith(href));
    const switchHref = (guild: (typeof data.guilds)[number]) => `/guild/${guild.id}${guild.canManage || section === "/music" ? section : ""}`;
    const members = (count: number) => `${count.toLocaleString("en-US")} ${count === 1 ? "member" : "members"}`;

    let switcherOpen = $state(false);
    let mobileSwitcherOpen = $state(false);
    let accountOpen = $state(false);
    let mobileAccountOpen = $state(false);
    afterNavigate(({ from, to }) => {
        switcherOpen = mobileSwitcherOpen = accountOpen = mobileAccountOpen = false;
        if (from?.url.pathname !== to?.url.pathname) details.close();
    });

    const focusRing = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";
    const stacked = "h-14 flex-col justify-center gap-0.5 rounded-2xl text-2xs";
</script>

{#snippet servers()}
    <nav aria-label="Servers" class="flex max-h-96 flex-col gap-1 overflow-y-auto overscroll-contain">
        {#each data.guilds as guild (guild.id)}
            <a
                href={switchHref(guild)}
                aria-current={guild.id === data.guild.id ? "page" : undefined}
                class="ripple flex h-12 shrink-0 items-center gap-4 rounded-xl px-2 text-sm font-medium hover:bg-white/10 aria-[current=page]:text-accent"
                {@attach ripple}
            >
                <GuildIcon src={guild.iconUrl} name={guild.name} class="size-8 rounded-lg text-mist-100" />
                <span class="min-w-0 flex-1 truncate">{guild.name}</span>
                {#if guild.id === data.guild.id}<MaterialSymbolsCheckRounded class="size-5 shrink-0" />{/if}
            </a>
        {/each}
    </nav>
    <hr class="my-2 border-white/10" />
    <a href="/guild" class="ripple flex h-12 items-center gap-4 rounded-xl px-4 text-sm font-medium hover:bg-white/10" {@attach ripple}>
        <MaterialSymbolsGridViewRounded class="size-5 text-mist-400" />All servers
    </a>
{/snippet}

{#snippet accountMenu()}
    {#if data.user}
        <div class="flex items-center gap-4 p-2 pb-4">
            <Avatar src={data.user.avatarUrl} name={data.user.name} class="size-12" />
            <div class="flex min-w-0 flex-col">
                <span class="truncate font-semibold">{data.user.name}</span>
                <span class="truncate font-mono text-sm text-mist-400">@{data.user.username}</span>
            </div>
        </div>
    {/if}
    <a href="/" class="ripple flex h-10 items-center gap-4 rounded-xl px-4 text-sm font-medium hover:bg-white/10" {@attach ripple}>
        <MaterialSymbolsHomeRounded class="size-5 text-mist-400" />Home
    </a>
    <form method="POST" action="/logout">
        <button
            class="ripple flex h-10 w-full items-center gap-4 rounded-xl px-4 text-sm font-medium text-red-400 hover:bg-red-400/10"
            {@attach ripple}
        >
            <MaterialSymbolsLogoutRounded class="size-5" />Log out
        </button>
    </form>
{/snippet}

{#snippet link(item: (typeof groups)[number]["items"][number], row: boolean)}
    <a
        href={item.href}
        aria-current={isCurrent(item.href) ? "page" : undefined}
        class={[
            "ripple flex shrink-0 items-center font-medium text-mist-400 hover:bg-white/10 hover:text-mist-100 aria-[current=page]:bg-accent/10 aria-[current=page]:text-accent",
            row ? "h-10 gap-2 rounded-full px-4 text-sm" : [stacked, "w-full"],
            focusRing,
        ]}
        {@attach ripple}
    >
        <item.icon class="size-6 shrink-0" />
        <span class="max-w-full truncate">{item.label}</span>
    </a>
{/snippet}

<div style:--sidebar="{width}px" style:--details={detailsOpen ? `${detailsWidth + 8}px` : "0px"}>
    <aside class="fixed inset-y-0 left-0 z-30 hidden w-(--sidebar) flex-col gap-4 overflow-hidden bg-surface-1 py-4 md:flex">
        <div class={["flex flex-col gap-4", expanded ? "px-4" : "items-center px-2"]}>
            <Popup
                bind:open={switcherOpen}
                title="Switch server"
                placement={expanded ? "bottom-start" : "right-start"}
                contentClass={expanded ? "w-(--reference-width)" : "w-72"}
                triggerClass={[
                    "ripple flex items-center text-left",
                    expanded ? "w-full gap-4 rounded-2xl bg-surface-2 p-2 pr-4 hover:bg-surface-3" : "rounded-2xl",
                    focusRing,
                ]}
            >
                {#snippet trigger()}
                    <GuildIcon src={data.guild.iconUrl} name={data.guild.name} class={expanded ? "size-10 rounded-xl" : "size-12 rounded-2xl"} />
                    {#if expanded}
                        <span class="flex min-w-0 flex-1 flex-col">
                            <span class="truncate text-sm font-semibold">{data.guild.name}</span>
                            <span class="font-mono text-xs text-mist-400">{members(data.guild.memberCount)}</span>
                        </span>
                        <MaterialSymbolsUnfoldMoreRounded class="size-5 shrink-0 text-mist-400" />
                    {/if}
                {/snippet}
                {@render servers()}
            </Popup>
        </div>

        <nav aria-label="Dashboard" class={["flex min-h-0 flex-1 scrollbar-none flex-col gap-6 overflow-y-auto py-2", expanded ? "px-4" : "px-2"]}>
            {#each groups as group, index (index)}
                <div class="flex flex-col gap-1">
                    {#if expanded && group.label}
                        <div class="flex items-center gap-2 px-4 pb-1">
                            <span class="font-mono text-2xs font-semibold tracking-wider text-mist-400 uppercase">{group.label}</span>
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

        {#if data.user}
            <div class={expanded ? "px-4" : "flex justify-center px-2"}>
                <Popup
                    bind:open={accountOpen}
                    title="Your account"
                    placement={expanded ? "top-start" : "right-end"}
                    triggerClass={[
                        "ripple flex items-center gap-4 rounded-full text-left hover:bg-surface-2",
                        expanded ? "w-full p-2 pr-4" : "p-2",
                        focusRing,
                    ]}
                >
                    {#snippet trigger()}
                        <Avatar src={data.user!.avatarUrl} name={data.user!.name} class="size-10" />
                        {#if expanded}
                            <span class="flex min-w-0 flex-1 flex-col">
                                <span class="truncate text-sm font-semibold">{data.user!.name}</span>
                                <span class="truncate font-mono text-xs text-mist-400">@{data.user!.username}</span>
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
        class="group fixed inset-y-2 left-(--sidebar) z-30 hidden w-2 cursor-col-resize justify-center md:flex"
        onpointerdown={resizeSidebar}
    >
        <span class="h-full w-1 rounded-full transition-colors duration-200 group-hover:bg-mist-400 group-active:bg-mist-400"></span>
    </div>

    <!-- The shadow paints the shell color around a rounded hole, so the content looks framed while the window still scrolls -->
    <div
        aria-hidden="true"
        class="pointer-events-none fixed inset-x-0 top-0 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-20 rounded-b-4xl shadow-[0_0_0_100vmax_var(--color-surface-1)] md:top-2 md:right-[calc(var(--details)+0.5rem)] md:bottom-2 md:left-[calc(var(--sidebar)+0.5rem)] md:rounded-4xl"
    ></div>

    <main
        class="px-4 pt-8 pb-[calc(6.5rem+env(safe-area-inset-bottom))] md:pt-10 md:pr-[calc(var(--details)+3rem)] md:pb-12 md:pl-[calc(var(--sidebar)+3rem)]"
    >
        {#key page.url.pathname}
            <div class="animate-page-in">{@render children()}</div>
        {/key}
    </main>

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
                class="group fixed inset-y-2 right-(--details) z-30 flex w-2 cursor-col-resize justify-center"
                onpointerdown={resizeDetails}
            >
                <span class="h-full w-1 rounded-full transition-colors duration-200 group-hover:bg-mist-400 group-active:bg-mist-400"></span>
            </div>
            <aside aria-label={details.title} class="fixed inset-y-2 right-2 z-30 flex w-[calc(var(--details)-0.5rem)] flex-col bg-surface-1">
                {#key details.key}
                    <div class="flex min-h-0 flex-1 animate-panel-in flex-col">
                        <div class="flex items-center gap-4 py-2 pr-2 pl-4">
                            <h2 class="min-w-0 flex-1 truncate font-display text-xl font-semibold">{details.title}</h2>
                            <Button variant="ghost" icon aria-label="Close panel" onclick={() => details.close()}
                                ><MaterialSymbolsCloseRounded /></Button
                            >
                        </div>
                        <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain p-4">{@render details.content()}</div>
                    </div>
                {/key}
            </aside>
        {/if}
    {/if}

    <nav aria-label="Dashboard" class="fixed inset-x-0 bottom-0 z-30 bg-surface-1 pt-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))] md:hidden">
        <div class="flex scrollbar-none overflow-x-auto">
            <div class="flex w-max min-w-full items-center justify-evenly gap-2 px-4">
                <Popup
                    bind:open={mobileSwitcherOpen}
                    title="Switch server"
                    triggerClass={["ripple flex w-16 shrink-0 items-center", stacked, focusRing]}
                >
                    {#snippet trigger()}
                        <GuildIcon src={data.guild.iconUrl} name={data.guild.name} class="size-6 rounded-lg" />
                        <span class="max-w-full truncate font-medium text-mist-400">Server</span>
                    {/snippet}
                    {@render servers()}
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
                            <span class="max-w-full truncate font-medium text-mist-400">You</span>
                        {/snippet}
                        {@render accountMenu()}
                    </Popup>
                {/if}
            </div>
        </div>
    </nav>
</div>
