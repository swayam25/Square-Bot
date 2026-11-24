<script lang="ts">
    import { ripple } from "#lib/attachments/ripple.ts";
    import { openInvitePopup } from "#lib/auth.ts";
    import Seo from "#lib/components/site/Seo.svelte";
    import SiteFooter from "#lib/components/site/SiteFooter.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import FilterChip from "#lib/components/ui/FilterChip.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import ScrollRow from "#lib/components/ui/ScrollRow.svelte";
    import Shape from "#lib/components/ui/Shape.svelte";
    import { focusRing } from "#lib/components/ui/styles.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { formatCount } from "#lib/format.ts";
    import { permissionNames } from "#lib/permissions.ts";
    import { scrollToElement } from "#lib/scroll.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { afterNavigate, invalidateAll, pushState, replaceState } from "$app/navigation";
    import { page } from "$app/state";
    import type { BotCommand, CommandOption } from "@square/api-client";
    import { onMount, type Component } from "svelte";
    import { cubicIn, cubicOut } from "svelte/easing";
    import { prefersReducedMotion } from "svelte/motion";
    import { SvelteSet } from "svelte/reactivity";
    import { slide } from "svelte/transition";
    import MaterialSymbolsAccountCircleRounded from "~icons/material-symbols/account-circle-rounded";
    import MaterialSymbolsCelebrationRounded from "~icons/material-symbols/celebration-rounded";
    import MaterialSymbolsCheckRounded from "~icons/material-symbols/check-rounded";
    import MaterialSymbolsChevronRightRounded from "~icons/material-symbols/chevron-right-rounded";
    import MaterialSymbolsCodeBlocksRounded from "~icons/material-symbols/code-blocks-rounded";
    import MaterialSymbolsConfirmationNumberRounded from "~icons/material-symbols/confirmation-number-rounded";
    import MaterialSymbolsContentCopyRounded from "~icons/material-symbols/content-copy-rounded";
    import MaterialSymbolsDataObjectRounded from "~icons/material-symbols/data-object-rounded";
    import MaterialSymbolsFormatQuoteRounded from "~icons/material-symbols/format-quote-rounded";
    import MaterialSymbolsGroupsRounded from "~icons/material-symbols/groups-rounded";
    import MaterialSymbolsInfoRounded from "~icons/material-symbols/info-rounded";
    import MaterialSymbolsLinkRounded from "~icons/material-symbols/link-rounded";
    import MaterialSymbolsLockRounded from "~icons/material-symbols/lock-rounded";
    import MaterialSymbolsMicRounded from "~icons/material-symbols/mic-rounded";
    import MaterialSymbolsMusicNoteRounded from "~icons/material-symbols/music-note-rounded";
    import MaterialSymbolsPersonAddRounded from "~icons/material-symbols/person-add-rounded";
    import MaterialSymbolsPublicRounded from "~icons/material-symbols/public-rounded";
    import MaterialSymbolsRightClickRounded from "~icons/material-symbols/right-click-rounded";
    import MaterialSymbolsSearchRounded from "~icons/material-symbols/search-rounded";
    import MaterialSymbolsSettingsRounded from "~icons/material-symbols/settings-rounded";
    import MaterialSymbolsShieldRounded from "~icons/material-symbols/shield-rounded";
    import MaterialSymbolsStarRounded from "~icons/material-symbols/star-rounded";
    import MaterialSymbolsToggleOnRounded from "~icons/material-symbols/toggle-on-rounded";
    import type { PageProps } from "./$types";

    let { data }: PageProps = $props();

    type Look = { icon: Component; ink: string; fill: string; lobes: number };

    const LOOKS: Record<string, Look> = {
        Moderation: { icon: MaterialSymbolsShieldRounded, ink: "text-red-400", fill: "text-red-400/10", lobes: 8 },
        "Mass Moderation": { icon: MaterialSymbolsGroupsRounded, ink: "text-red-400", fill: "text-red-400/10", lobes: 5 },
        Voice: { icon: MaterialSymbolsMicRounded, ink: "text-violet-300", fill: "text-violet-500/20", lobes: 7 },
        Info: { icon: MaterialSymbolsInfoRounded, ink: "text-gray-100", fill: "text-white/10", lobes: 6 },
        Settings: { icon: MaterialSymbolsSettingsRounded, ink: "text-gray-100", fill: "text-white/10", lobes: 9 },
        Music: { icon: MaterialSymbolsMusicNoteRounded, ink: "text-accent", fill: "text-accent/10", lobes: 10 },
        Tickets: { icon: MaterialSymbolsConfirmationNumberRounded, ink: "text-amber-400", fill: "text-amber-400/10", lobes: 4 },
        Invites: { icon: MaterialSymbolsPersonAddRounded, ink: "text-emerald-400", fill: "text-emerald-400/10", lobes: 6 },
        Giveaways: { icon: MaterialSymbolsCelebrationRounded, ink: "text-violet-300", fill: "text-violet-500/20", lobes: 8 },
        Starboard: { icon: MaterialSymbolsStarRounded, ink: "text-amber-400", fill: "text-amber-400/10", lobes: 5 },
        Quote: { icon: MaterialSymbolsFormatQuoteRounded, ink: "text-emerald-400", fill: "text-emerald-400/10", lobes: 7 },
        Utility: { icon: MaterialSymbolsDataObjectRounded, ink: "text-violet-300", fill: "text-violet-500/20", lobes: 5 },
    };
    const FALLBACK: Look = { icon: MaterialSymbolsCodeBlocksRounded, ink: "text-gray-100", fill: "text-white/10", lobes: 6 };

    const TYPES: Record<CommandOption["type"], string> = {
        string: "Text",
        integer: "Whole number",
        number: "Number",
        boolean: "True or false",
        user: "User",
        channel: "Channel",
        role: "Role",
        mentionable: "User or role",
        attachment: "File",
    };
    const CHANNELS: Record<string, string> = {
        text: "text",
        news: "announcement",
        voice: "voice",
        stage_voice: "stage",
        category: "category",
        forum: "forum",
        media: "media",
    };
    const INSTALLS: Record<BotCommand["install"], string> = { server: "", both: "Anywhere", account: "Account only" };
    const either = new Intl.ListFormat("en", { type: "disjunction" });

    const slug = (value: string) => value.toLowerCase().replaceAll(" ", "-");

    const categories = $derived(
        (data.categories ?? []).map((category) => ({
            name: category.name,
            description: category.description,
            module: category.module,
            id: slug(category.name),
            look: LOOKS[category.name] ?? FALLBACK,
            entries: category.commands.map((command) => {
                const perms = command.permissions ? permissionNames(command.permissions) : [];
                return {
                    command,
                    perms,
                    id: command.kind === "slash" ? `/${slug(command.name)}` : `${command.kind}/${slug(command.name)}`,
                    text: [command.name, command.description, category.name, ...perms, INSTALLS[command.install]].join(" ").toLowerCase(),
                    options: command.options
                        .map((option) => [option.name, option.description, ...option.choices].join(" "))
                        .join(" ")
                        .toLowerCase(),
                };
            }),
        })),
    );
    const total = $derived(categories.reduce((sum, category) => sum + category.entries.length, 0));

    let query = $state(page.url.searchParams.get("q") ?? "");
    let search = $state<HTMLInputElement | null>(null);
    let results = $state<HTMLElement>();

    // `lg:top-28` of the sticky sidebar, in px
    const STICKY = 112;

    const terms = $derived(query.toLowerCase().trim().replace(/^\//, "").split(/\s+/).filter(Boolean));
    const shown = $derived(
        categories.map((category) => ({
            ...category,
            entries: category.entries.filter((entry) => terms.every((term) => entry.text.includes(term) || entry.options.includes(term))),
        })),
    );
    const found = $derived(shown.reduce((sum, category) => sum + category.entries.length, 0));
    const pattern = $derived(
        terms.length ? new RegExp(`(${terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi") : null,
    );

    type Entry = (typeof categories)[number]["entries"][number];

    // A search that only hits an option opens its row so the hit shows. `shut` keeps rows closed by hand closed
    const opened = new SvelteSet<string>();
    const shut = new SvelteSet<string>();
    const optionHit = (entry: Entry) => terms.length > 0 && !terms.every((term) => entry.text.includes(term));
    const isOpen = (entry: Entry) => (opened.has(entry.id) || optionHit(entry)) && !shut.has(entry.id);

    function toggle(entry: Entry) {
        if (isOpen(entry)) {
            opened.delete(entry.id);
            shut.add(entry.id);
        } else {
            shut.delete(entry.id);
            opened.add(entry.id);
        }
    }

    $effect(() => {
        const url = new URL(location.href);
        const value = query.trim();
        if (value) url.searchParams.set("q", value);
        else url.searchParams.delete("q");
        if (url.href === location.href) return;
        replaceState(url, {});
        // A shorter list would pull the sticky search out of view mid-typing
        const top = results?.getBoundingClientRect().top ?? 0;
        if (top < STICKY) scrollTo({ top: scrollY + top - STICKY });
    });

    onMount(() => {
        const reveal = () => {
            const id = decodeURIComponent(location.hash.slice(1));
            if (!/^(user|message)?\//.test(id)) return;
            shut.delete(id);
            opened.add(id);
        };
        reveal();
        addEventListener("hashchange", reveal);
        return () => removeEventListener("hashchange", reveal);
    });

    let active = $state<string | null>(null);
    let pinned = false;

    function go(id: string) {
        const target = document.getElementById(id);
        if (!target) return;
        active = target.closest("section[id]")?.id ?? active;
        pinned = true;
        scrollToElement(target);
    }

    function jump(event: MouseEvent, id: string) {
        if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        if (location.hash !== `#${id}`) pushState(`#${id}`, {});
        go(id);
    }

    afterNavigate(({ type }) => {
        const id = decodeURIComponent(location.hash.slice(1));
        if (!id || !document.getElementById(id)) return;
        const entry = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
        if (type !== "link" && type !== "goto" && !(type === "enter" && entry?.type === "navigate")) return;
        scrollTo({ top: 0, behavior: "instant" });
        go(id);
    });

    function spy(root: HTMLElement) {
        let frame = 0;
        const update = () => {
            frame = 0;
            if (pinned) return;
            const sections = [...root.querySelectorAll<HTMLElement>("section[id]")];
            const bottom = innerHeight + scrollY >= document.documentElement.scrollHeight - 2;
            active =
                (bottom ? sections.at(-1) : sections.findLast((section) => section.getBoundingClientRect().top <= 128))?.id ??
                sections[0]?.id ??
                null;
        };
        const schedule = () => (frame ||= requestAnimationFrame(update));
        const unpin = () => (pinned = false);
        schedule();
        addEventListener("scroll", schedule, { passive: true });
        addEventListener("resize", schedule, { passive: true });
        for (const type of ["wheel", "touchstart", "keydown", "pointerdown"]) addEventListener(type, unpin, { passive: true });
        return () => {
            cancelAnimationFrame(frame);
            removeEventListener("scroll", schedule);
            removeEventListener("resize", schedule);
            for (const type of ["wheel", "touchstart", "keydown", "pointerdown"]) removeEventListener(type, unpin);
        };
    }

    function onkeydown(event: KeyboardEvent) {
        if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
        if (event.target instanceof Element && event.target.closest("input, textarea, select, [contenteditable]")) return;
        event.preventDefault();
        search?.focus();
    }

    let copied = $state<string | null>(null);
    let copiedTimer: ReturnType<typeof setTimeout> | undefined;

    async function copy(key: string, text: string) {
        try {
            await navigator.clipboard.writeText(text);
        } catch {
            toast.error("Your browser didn't allow copying");
            return;
        }
        copied = key;
        clearTimeout(copiedTimer);
        copiedTimer = setTimeout(() => (copied = null), 1500);
    }

    function range(option: CommandOption) {
        const { min, max } = option;
        if (min != null && max != null) return `${min}–${max}`;
        if (min != null) return `${min} or more`;
        if (max != null) return `Up to ${max}`;
        return null;
    }

    function details(option: CommandOption) {
        const kinds = option.channelTypes.map((kind) => CHANNELS[kind] ?? kind);
        const type = option.type === "channel" && kinds.length ? `${either.format(kinds)} channel` : TYPES[option.type];
        return [
            type.charAt(0).toUpperCase() + type.slice(1),
            option.required ? "Required" : "Optional",
            range(option),
            option.autocomplete && "Suggests as you type",
        ].filter((part): part is string => !!part);
    }
</script>

<svelte:window {onkeydown} />

<Seo title="Commands" description="Every Square command, with its options and the permissions it needs." />

{#snippet marked(text: string)}{#each pattern ? text.split(pattern) : [text] as part, index (index)}{#if index % 2}<mark
                class="bg-transparent text-accent"
            >
                {part}
            </mark>{:else}{part}{/if}{/each}{/snippet}

{#snippet token(name: string, required: boolean)}
    <code
        class={[
            "inline-flex h-6 items-center rounded-lg px-2 font-mono text-xs",
            required ? "bg-white/10 text-gray-100" : "bg-white/5 text-gray-400",
        ]}
    >
        {name}{#if !required}?{/if}
    </code>
{/snippet}

<!-- Spans only: a row that opens renders this inside a button, which takes phrasing content -->
{#snippet head(command: BotCommand, perms: string[], expandable: boolean, open: boolean)}
    <span class="flex items-start gap-2 rounded-2xl py-2 pr-4 pl-4 transition-colors group-hover/row:bg-gray-900 sm:pr-20">
        <MaterialSymbolsChevronRightRounded
            aria-hidden="true"
            class={["mt-1 size-4 shrink-0 text-gray-400 transition-transform duration-200 ease-out", open && "rotate-90", !expandable && "invisible"]}
        />
        <span class="flex min-w-0 flex-1 flex-col gap-2">
            <span class="flex flex-wrap items-center gap-2">
                {#if command.kind === "slash"}
                    <code class="font-mono text-sm font-semibold text-gray-100">
                        <span class="text-accent">/</span>{@render marked(command.name)}
                    </code>
                    {#each command.options as option (option.name)}{@render token(option.name, option.required)}{/each}
                {:else}
                    <code class="flex items-center gap-2 font-mono text-sm font-semibold text-gray-100">
                        <MaterialSymbolsRightClickRounded aria-hidden="true" class="size-4 text-accent" />Apps
                        <MaterialSymbolsChevronRightRounded aria-hidden="true" class="size-4 text-gray-400" />{@render marked(command.name)}
                    </code>
                    <Chip size="sm" tone="muted">Right-click a {command.kind === "message" ? "message" : "member"}</Chip>
                {/if}
                {#if perms.length || command.install !== "server"}
                    <span class="flex flex-wrap gap-2 sm:ml-auto">
                        {#if command.install === "both"}
                            <Tooltip
                                lazy
                                content="Works in servers with Square. Add Square to your account and it also works in DMs and servers without Square"
                            >
                                <Chip size="sm" tone="muted"><MaterialSymbolsPublicRounded />{@render marked(INSTALLS.both)}</Chip>
                            </Tooltip>
                        {:else if command.install === "account"}
                            <Tooltip lazy content="Only for people who added Square to their account. Then it works in every server and DM">
                                <Chip size="sm" tone="muted"><MaterialSymbolsAccountCircleRounded />{@render marked(INSTALLS.account)}</Chip>
                            </Tooltip>
                        {/if}
                        {#each perms as perm (perm)}
                            <Tooltip lazy content="Only members with {perm} see this, unless a server admin changes it under Integrations">
                                <Chip size="sm" tone="muted"><MaterialSymbolsLockRounded />{@render marked(perm)}</Chip>
                            </Tooltip>
                        {/each}
                    </span>
                {/if}
            </span>
            <span class="text-sm text-gray-400">{@render marked(command.description)}</span>
        </span>
    </span>
{/snippet}

<div class="mx-auto max-w-6xl px-4 pt-32 md:px-6 md:pt-40">
    <header class="flex flex-col gap-4 pb-12">
        <h1 class="font-display text-4xl font-semibold tracking-tight md:text-5xl">Commands</h1>
        <p class="max-w-2xl text-gray-400 md:text-lg">Everything Square does in Discord, with every option and the permission it needs.</p>
        {#if data.categories}
            <p class="flex flex-wrap items-center gap-2 font-mono text-xs text-gray-400">
                <span aria-live="polite">{terms.length ? `${formatCount(found)} of ${formatCount(total)}` : formatCount(total)} commands</span>
                <span aria-hidden="true">·</span>
                <span>{formatCount(categories.length)} categories</span>
                <span aria-hidden="true">·</span>
                <span class="flex items-center gap-2">{@render token("name", true)} required</span>
                <span class="flex items-center gap-2">{@render token("name", false)} optional</span>
                <span aria-hidden="true">·</span>
                <a
                    href={data.installUrl}
                    target="_blank"
                    rel="noopener"
                    onclick={openInvitePopup}
                    class="flex flex-wrap items-center gap-2 text-gray-400 transition-colors hover:text-gray-100"
                >
                    <Chip size="sm" tone="muted"><MaterialSymbolsPublicRounded />{INSTALLS.both}</Chip>
                    <Chip size="sm" tone="muted"><MaterialSymbolsAccountCircleRounded />{INSTALLS.account}</Chip>
                    <span>work everywhere after you add Square to your account</span>
                </a>
            </p>
        {/if}
    </header>

    {#if !data.categories}
        <EmptyState
            card
            tone="danger"
            title="Couldn't load the commands"
            text="Square isn't answering right now. Try again in a moment."
            retry={invalidateAll}
        />
    {:else}
        <div bind:this={results} class="grid gap-8 lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-12">
            <aside class="flex min-w-0 flex-col gap-4 lg:sticky lg:top-28 lg:self-start">
                <div class="relative">
                    <Input
                        bind:ref={search}
                        bind:value={query}
                        type="search"
                        icon={MaterialSymbolsSearchRounded}
                        placeholder="Search commands"
                        aria-label="Search commands"
                    />
                    {#if !query}
                        <kbd
                            aria-hidden="true"
                            class="pointer-events-none absolute top-1/2 right-3 flex size-6 -translate-y-1/2 items-center justify-center rounded-lg bg-white/10 font-mono text-xs text-gray-400 pointer-coarse:hidden"
                        >
                            /
                        </kbd>
                    {/if}
                </div>
                <ScrollRow class="lg:hidden">
                    {#each shown as category (category.id)}
                        {#if category.entries.length}
                            <FilterChip checked={active === category.id} onclick={() => go(category.id)}>
                                <category.look.icon />{category.name}
                            </FilterChip>
                        {/if}
                    {/each}
                </ScrollRow>
                <nav aria-label="Categories" class="hidden flex-col lg:flex">
                    {#each shown as category (category.id)}
                        {@const current = active === category.id && category.entries.length > 0}
                        <a
                            href="#{category.id}"
                            aria-disabled={!category.entries.length || undefined}
                            onclick={(event) => jump(event, category.id)}
                            class={[
                                "ripple flex h-10 items-center gap-3 rounded-2xl px-3 text-sm font-medium transition-colors [&>svg]:size-5 [&>svg]:shrink-0",
                                current ? "bg-gray-900 text-gray-100" : "text-gray-400 hover:bg-gray-900 hover:text-gray-100",
                                !category.entries.length && "pointer-events-none opacity-50",
                            ]}
                            {@attach ripple}
                        >
                            <category.look.icon class={current ? category.look.ink : undefined} />
                            <span class="min-w-0 flex-1 truncate">{category.name}</span>
                            <span class="font-mono text-xs text-gray-400">{formatCount(category.entries.length)}</span>
                        </a>
                    {/each}
                </nav>
            </aside>

            <div class="flex min-w-0 flex-col gap-12" {@attach spy}>
                {#each shown as category (category.id)}
                    {#if category.entries.length}
                        <section id={category.id} aria-labelledby="{category.id}-title" class="flex scroll-mt-28 flex-col gap-4">
                            <div class="flex items-center gap-4">
                                <span class="relative flex size-12 shrink-0 items-center justify-center">
                                    <Shape
                                        lobes={category.look.lobes}
                                        depth={category.look.lobes < 6 ? 0.16 : 0.1}
                                        class={["absolute inset-0 size-full", category.look.fill]}
                                    />
                                    <category.look.icon class={["relative size-6", category.look.ink]} />
                                </span>
                                <div class="flex min-w-0 flex-1 flex-col">
                                    <h2 id="{category.id}-title" class="flex items-baseline gap-2 font-display text-2xl font-semibold">
                                        {category.name}<span class="font-mono text-sm font-normal text-gray-400">
                                            {formatCount(category.entries.length)}
                                        </span>
                                    </h2>
                                    <p class="text-sm text-gray-400">{category.description}</p>
                                </div>
                                {#if category.module}
                                    <Tooltip lazy content="These work while {category.name} is turned on in the dashboard">
                                        <Chip size="sm" tone="muted"><MaterialSymbolsToggleOnRounded />Module</Chip>
                                    </Tooltip>
                                {/if}
                            </div>

                            <ul class="flex flex-col gap-2">
                                {#each category.entries as entry (entry.id)}
                                    {@const { command, perms } = entry}
                                    {@const open = isOpen(entry)}
                                    <li
                                        id={entry.id}
                                        class={[
                                            "group/row relative scroll-mt-28 rounded-2xl transition-colors duration-200 ease-out target:bg-accent/10",
                                            open && "bg-gray-900",
                                        ]}
                                    >
                                        {#if command.options.length}
                                            <button
                                                type="button"
                                                aria-expanded={open}
                                                aria-controls="{entry.id}-options"
                                                class={["block w-full cursor-pointer rounded-2xl text-left", focusRing]}
                                                onclick={() => toggle(entry)}
                                            >
                                                {@render head(command, perms, true, open)}
                                            </button>
                                            {#if open}
                                                <dl
                                                    id="{entry.id}-options"
                                                    in:slide={{ duration: prefersReducedMotion.current ? 0 : 200, easing: cubicOut }}
                                                    out:slide={{ duration: prefersReducedMotion.current ? 0 : 150, easing: cubicIn }}
                                                    class="flex flex-col gap-4 pt-2 pr-4 pb-4 pl-10"
                                                >
                                                    {#each command.options as option (option.name)}
                                                        <div class="flex flex-col gap-2 sm:flex-row sm:gap-4">
                                                            <dt
                                                                class={[
                                                                    "shrink-0 font-mono text-sm sm:w-36",
                                                                    option.required ? "text-gray-100" : "text-gray-400",
                                                                ]}
                                                            >
                                                                {@render marked(option.name)}{#if !option.required}?{/if}
                                                            </dt>
                                                            <dd class="flex min-w-0 flex-col gap-2">
                                                                <span class="text-sm text-gray-100">{@render marked(option.description)}</span>
                                                                <span class="flex flex-wrap items-center gap-2 text-xs text-gray-400">
                                                                    {#each details(option) as part, index (part)}
                                                                        {#if index}<span aria-hidden="true">·</span>{/if}<span>{part}</span>
                                                                    {/each}
                                                                </span>
                                                                {#if option.choices.length}
                                                                    <span class="flex flex-wrap gap-2">
                                                                        {#each option.choices as choice (choice)}
                                                                            <Chip size="sm">
                                                                                <code class="font-mono">{@render marked(choice)}</code>
                                                                            </Chip>
                                                                        {/each}
                                                                    </span>
                                                                {/if}
                                                            </dd>
                                                        </div>
                                                    {/each}
                                                </dl>
                                            {/if}
                                        {:else}
                                            {@render head(command, perms, false, false)}
                                        {/if}
                                        <div
                                            class="absolute top-2 right-2 flex gap-2 transition-opacity duration-200 ease-out group-hover/row:opacity-100 group-has-focus-visible/row:opacity-100 max-sm:hidden pointer-fine:opacity-0"
                                        >
                                            {#if command.kind === "slash"}
                                                <Tooltip content={copied === entry.id ? "Copied" : "Copy command"}>
                                                    <Button variant="ghost" size="xs" icon onclick={() => copy(entry.id, `/${command.name}`)}>
                                                        {#if copied === entry.id}<MaterialSymbolsCheckRounded
                                                            />{:else}<MaterialSymbolsContentCopyRounded />{/if}
                                                    </Button>
                                                </Tooltip>
                                            {/if}
                                            <Tooltip content={copied === `link:${entry.id}` ? "Copied" : "Copy link"}>
                                                <Button
                                                    variant="ghost"
                                                    size="xs"
                                                    icon
                                                    onclick={() => copy(`link:${entry.id}`, `${page.url.origin}${page.url.pathname}#${entry.id}`)}
                                                >
                                                    {#if copied === `link:${entry.id}`}<MaterialSymbolsCheckRounded
                                                        />{:else}<MaterialSymbolsLinkRounded />{/if}
                                                </Button>
                                            </Tooltip>
                                        </div>
                                    </li>
                                {/each}
                            </ul>
                        </section>
                    {/if}
                {/each}

                {#if !found}
                    <EmptyState
                        card
                        icon={MaterialSymbolsSearchRounded}
                        title="No commands match “{query.trim()}”"
                        text="Try a shorter word, an option or a permission name."
                    />
                {/if}
            </div>
        </div>
    {/if}
</div>

<SiteFooter inviteUrl={data.inviteUrl} installUrl={data.installUrl} />
