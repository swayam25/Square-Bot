<script lang="ts">
    import { edgeFade } from "#lib/attachments/edge-fade.ts";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import GuildIcon from "#lib/components/ui/GuildIcon.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import OverlayScrollbar from "#lib/components/ui/OverlayScrollbar.svelte";
    import Popup from "#lib/components/ui/Popup.svelte";
    import { focusRing } from "#lib/components/ui/styles.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { emojiData, guildEmojis } from "#lib/emoji/emoji.remote.ts";
    import {
        addRecent,
        customToken,
        customUrl,
        emojiScore,
        GROUPS,
        loadRecent,
        loadTone,
        saveTone,
        shortcodeOf,
        TONE_NAMES,
        toned,
        TONES,
        type GroupKey,
        type GuildEmoji,
        type UnicodeEmoji,
    } from "#lib/emoji/emoji.ts";
    import { mobile } from "#lib/media.ts";
    import { tick, untrack, type Component } from "svelte";
    import type { ClassValue } from "svelte/elements";
    import MaterialSymbolsAddReactionRounded from "~icons/material-symbols/add-reaction-rounded";
    import MaterialSymbolsEmojiFoodBeverageRounded from "~icons/material-symbols/emoji-food-beverage-rounded";
    import MaterialSymbolsEmojiNatureRounded from "~icons/material-symbols/emoji-nature-rounded";
    import MaterialSymbolsEmojiObjectsRounded from "~icons/material-symbols/emoji-objects-rounded";
    import MaterialSymbolsEmojiPeopleRounded from "~icons/material-symbols/emoji-people-rounded";
    import MaterialSymbolsEmojiSymbolsRounded from "~icons/material-symbols/emoji-symbols-rounded";
    import MaterialSymbolsEmojiTransportationRounded from "~icons/material-symbols/emoji-transportation-rounded";
    import MaterialSymbolsFlagRounded from "~icons/material-symbols/flag-rounded";
    import MaterialSymbolsHistoryRounded from "~icons/material-symbols/history-rounded";
    import MaterialSymbolsMoodRounded from "~icons/material-symbols/mood-rounded";
    import MaterialSymbolsSearchOffRounded from "~icons/material-symbols/search-off-rounded";
    import MaterialSymbolsSearchRounded from "~icons/material-symbols/search-rounded";
    import MaterialSymbolsSportsSoccerRounded from "~icons/material-symbols/sports-soccer-rounded";

    let {
        guild,
        onpick,
        finalFocus,
        disabled = false,
        triggerClass,
        placement = "bottom-end",
    }: {
        guild?: { id: string; name: string; iconUrl: string | null };
        onpick: (text: string) => void;
        finalFocus?: () => HTMLElement | null;
        disabled?: boolean;
        triggerClass?: ClassValue;
        placement?: "bottom-start" | "bottom-end" | "top-start" | "top-end";
    } = $props();

    type UnicodeCell = { key: string; kind: "unicode"; emoji: UnicodeEmoji };
    type CustomCell = { key: string; kind: "custom"; emoji: GuildEmoji };
    type Cell = UnicodeCell | CustomCell;
    type Section = { key: string; name: string; cells: Cell[] };

    const ICONS: Record<GroupKey | "recent", Component> = {
        recent: MaterialSymbolsHistoryRounded,
        smileys: MaterialSymbolsMoodRounded,
        people: MaterialSymbolsEmojiPeopleRounded,
        nature: MaterialSymbolsEmojiNatureRounded,
        food: MaterialSymbolsEmojiFoodBeverageRounded,
        travel: MaterialSymbolsEmojiTransportationRounded,
        activities: MaterialSymbolsSportsSoccerRounded,
        objects: MaterialSymbolsEmojiObjectsRounded,
        symbols: MaterialSymbolsEmojiSymbolsRounded,
        flags: MaterialSymbolsFlagRounded,
    };
    const CELL = 40;
    const HEADER = 32;

    let open = $state(false);
    let wanted = $state(false);
    let attempt = $state(0);
    let search = $state("");
    let tone = $state(0);
    let toneOpen = $state(false);
    let recent = $state<string[]>([]);
    let hovered = $state<Cell | null>(null);
    let roving = $state("");
    let active = $state("");
    let cols = $state(10);
    let scroller = $state<HTMLElement | null>(null);
    let input = $state<HTMLInputElement | null>(null);

    $effect.pre(() => {
        if (!open) return;
        untrack(() => {
            wanted = true;
            search = "";
            toneOpen = false;
            hovered = null;
            roving = "";
            tone = loadTone();
            recent = loadRecent();
            scroller?.scrollTo(0, 0);
        });
    });

    const dataQuery = $derived.by(() => {
        void attempt;
        return wanted ? emojiData() : null;
    });
    const customQuery = $derived(wanted && guild ? guildEmojis(guild.id) : null);

    const data = $derived(dataQuery?.current);
    const customs = $derived(customQuery?.current ?? []);
    const customsSettled = $derived(!customQuery || customQuery.current !== undefined || !!customQuery.error);

    const groups = $derived(
        data
            ? GROUPS.map(({ key, name }) => ({
                  key,
                  name,
                  cells: data[key].map((emoji): UnicodeCell => ({ key: emoji[0], kind: "unicode", emoji })),
              }))
            : [],
    );
    const unicodeCells = $derived(new Map(groups.flatMap((section) => section.cells).map((cell) => [cell.key, cell])));
    const customCells = $derived(customs.map((emoji): CustomCell => ({ key: `c:${emoji.id}`, kind: "custom", emoji })));

    const query = $derived(search.trim().toLowerCase().replaceAll(":", ""));

    const results = $derived.by<Cell[]>(() => {
        if (!query) return [];
        const ranked: [number, Cell][] = [];
        for (const cell of customCells) {
            const name = cell.emoji.name.toLowerCase();
            const rank = emojiScore(query, name, name, name);
            if (rank >= 0) ranked.push([rank, cell]);
        }
        for (const cell of unicodeCells.values()) {
            const [, label, shortcodes, terms] = cell.emoji;
            const rank = emojiScore(query, shortcodes, label.toLowerCase(), terms);
            if (rank >= 0) ranked.push([rank, cell]);
        }
        return ranked.sort((a, b) => a[0] - b[0]).map(([, cell]) => cell);
    });

    const browse = $derived.by<Section[]>(() => {
        const byCustom = new Map(customCells.map((cell) => [cell.key, cell]));
        const recentCells = recent.flatMap((key) => byCustom.get(key) ?? unicodeCells.get(key) ?? []);
        return [
            ...(recentCells.length ? [{ key: "recent", name: "Recently used", cells: recentCells }] : []),
            ...(guild && (customCells.length || customQuery?.error) ? [{ key: "server", name: guild.name, cells: customCells }] : []),
            ...groups,
        ];
    });
    const sections = $derived<Section[]>(query ? [{ key: "results", name: "Search results", cells: results }] : browse);

    const preview = $derived(hovered ?? (query ? results[0] : undefined));

    $effect(() => {
        const el = scroller;
        if (!el) return;
        const observer = new ResizeObserver(() => (cols = Math.max(1, Math.floor(el.clientWidth / CELL))));
        observer.observe(el);
        return () => observer.disconnect();
    });

    $effect(() => {
        void sections;
        spy();
    });

    function spy() {
        if (!scroller) return;
        const top = scroller.scrollTop + HEADER;
        let current = "";
        for (const el of scroller.querySelectorAll<HTMLElement>("[data-section]")) {
            if (el.offsetTop > top) break;
            current = el.dataset.section ?? "";
        }
        active = current;
    }

    async function jump(key: string) {
        search = "";
        await tick();
        const el = scroller?.querySelector<HTMLElement>(`[data-section="${key}"]`);
        if (scroller && el) scroller.scrollTop = el.offsetTop;
        active = key;
    }

    function usable(cell: Cell) {
        return cell.kind === "unicode" || cell.emoji.usable;
    }

    function textOf(cell: Cell) {
        return cell.kind === "custom" ? customToken(cell.emoji) : toned(cell.emoji, tone);
    }

    function pick(cell: Cell, keep: boolean) {
        if (!usable(cell)) return;
        onpick(textOf(cell));
        addRecent(loadRecent(), cell.key);
        if (!keep) open = false;
    }

    function setTone(next: number) {
        tone = next;
        saveTone(next);
        toneOpen = false;
    }

    function navigate(event: KeyboardEvent) {
        const cell = (event.target as HTMLElement).closest<HTMLElement>("[data-cell]");
        const grid = cell?.parentElement;
        if (!cell || !grid || !scroller) return;
        const grids = [...scroller.querySelectorAll<HTMLElement>("[data-grid]")];
        const at = grids.indexOf(grid);
        const items = [...grid.children] as HTMLElement[];
        const i = items.indexOf(cell);
        const column = i % cols;
        const lastRow = Math.floor((items.length - 1) / cols);
        let target: Element | null | undefined;
        switch (event.key) {
            case "ArrowRight":
                target = items[i + 1] ?? grids[at + 1]?.firstElementChild;
                break;
            case "ArrowLeft":
                target = items[i - 1] ?? grids[at - 1]?.lastElementChild;
                break;
            case "ArrowDown": {
                const next = grids[at + 1];
                if (i + cols < items.length) target = items[i + cols];
                else if (Math.floor(i / cols) < lastRow) target = items.at(-1);
                else if (next) target = next.children[Math.min(column, next.children.length - 1)];
                break;
            }
            case "ArrowUp": {
                const previous = grids[at - 1];
                if (i >= cols) target = items[i - cols];
                else if (previous) {
                    const count = previous.children.length;
                    target = previous.children[Math.min(Math.floor((count - 1) / cols) * cols + column, count - 1)];
                } else target = input;
                break;
            }
            default:
                return;
        }
        event.preventDefault();
        (target as HTMLElement | null | undefined)?.focus();
    }

    function onSearchKey(event: KeyboardEvent) {
        if (event.key === "Enter" && results[0]) {
            event.preventDefault();
            pick(results[0], event.shiftKey);
        } else if (event.key === "ArrowDown") {
            event.preventDefault();
            scroller?.querySelector<HTMLElement>("[data-cell]")?.focus();
        }
    }

    const railButton = [
        "ripple flex h-8 min-w-8 flex-1 items-center justify-center rounded-xl text-gray-400 hover:bg-white/10 hover:text-gray-100 [&>svg]:size-5",
        focusRing,
    ];
    const surface = $derived(mobile.current ? "bg-gray-900" : "bg-gray-800");
</script>

{#snippet glyph(cell: Cell, play = false)}
    {#if cell.kind === "custom"}
        <img
            src={customUrl(cell.emoji, play || hovered?.key === cell.key)}
            alt=":{cell.emoji.name}:"
            draggable="false"
            loading="lazy"
            class={["size-8 object-contain", !cell.emoji.usable && "opacity-40 grayscale"]}
        />
    {:else}
        <span class="font-emoji text-3xl/none">{toned(cell.emoji, tone)}</span>
    {/if}
{/snippet}

<Tooltip content="Emoji">
    <Popup
        bind:open
        title="Emoji"
        {placement}
        {disabled}
        {finalFocus}
        plain
        contentClass="w-104"
        triggerClass={[
            "ripple flex size-10 shrink-0 items-center justify-center rounded-2xl text-gray-400 hover:bg-white/10 hover:text-gray-100 disabled:opacity-50 md:size-8 md:rounded-xl [&>svg]:size-5",
            focusRing,
            triggerClass,
        ]}
    >
        {#snippet trigger()}<MaterialSymbolsAddReactionRounded />{/snippet}

        <div class={["flex flex-col gap-2", mobile.current ? "h-[70dvh] px-4 pb-4" : "h-112 max-h-[calc(var(--available-height)-1rem)]"]}>
            <div class="relative flex items-center gap-2">
                <Input
                    type="search"
                    icon={MaterialSymbolsSearchRounded}
                    placeholder="Search emoji"
                    aria-label="Search emoji"
                    autocomplete="off"
                    spellcheck="false"
                    class={mobile.current ? undefined : "bg-gray-900! hover:bg-gray-950!"}
                    bind:ref={input}
                    bind:value={search}
                    onkeydown={onSearchKey}
                />
                <Tooltip content="Skin tone">
                    <button
                        type="button"
                        aria-expanded={toneOpen}
                        class={[
                            "ripple flex size-12 shrink-0 items-center justify-center rounded-control-lg hover:bg-white/10 md:size-10 md:rounded-2xl",
                            focusRing,
                        ]}
                        onclick={() => (toneOpen = !toneOpen)}
                    >
                        <span class="font-emoji text-2xl/none">{TONES[tone]}</span>
                    </button>
                </Tooltip>
                {#if toneOpen}
                    <div
                        role="toolbar"
                        tabindex="-1"
                        aria-label="Skin tone"
                        class={[
                            "absolute inset-y-0 right-0 flex origin-right animate-pop-in items-center gap-1 rounded-control-lg p-1 shadow-xl shadow-black/50 md:rounded-2xl",
                            mobile.current ? "bg-gray-800" : "bg-gray-900",
                        ]}
                        onkeydown={(event) => {
                            if (event.key !== "Escape") return;
                            event.stopPropagation();
                            toneOpen = false;
                        }}
                        {@attach (node) => node.querySelector<HTMLElement>("[aria-pressed=true]")?.focus()}
                        onfocusout={(event) => {
                            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) toneOpen = false;
                        }}
                    >
                        {#each TONES as hand, index (hand)}
                            <Tooltip content={TONE_NAMES[index]}>
                                <button
                                    type="button"
                                    aria-pressed={tone === index}
                                    class={[
                                        "ripple flex size-10 items-center justify-center rounded-2xl hover:bg-white/10 aria-pressed:bg-accent/20 md:size-8 md:rounded-xl",
                                        focusRing,
                                    ]}
                                    onclick={() => setTone(index)}
                                >
                                    <span class="font-emoji text-2xl/none">{hand}</span>
                                </button>
                            </Tooltip>
                        {/each}
                    </div>
                {/if}
            </div>

            <div class="edge-fade-x -mx-1 flex scrollbar-none overflow-x-auto px-1 py-1" {@attach edgeFade("x")}>
                <div class="flex w-full min-w-max gap-1">
                    {#each browse as section (section.key)}
                        <Tooltip content={section.key === "server" ? "Server emojis" : section.name} class="flex-1">
                            <button
                                type="button"
                                aria-pressed={!query && active === section.key}
                                class={[railButton, "w-full aria-pressed:bg-accent/20 aria-pressed:text-accent"]}
                                onclick={() => jump(section.key)}
                            >
                                {#if section.key === "server" && guild}
                                    <GuildIcon src={guild.iconUrl} name={guild.name} class="size-5 rounded-md text-2xs" />
                                {:else}
                                    {@const Icon = ICONS[section.key as GroupKey | "recent"]}
                                    <Icon />
                                {/if}
                            </button>
                        </Tooltip>
                    {/each}
                </div>
            </div>

            <div class="relative min-h-0 flex-1">
                <div
                    bind:this={scroller}
                    role="presentation"
                    class={["relative h-full scroll-pt-8 overflow-y-auto overscroll-contain", !mobile.current && "-mr-2 pr-3"]}
                    onscroll={spy}
                    onkeydown={navigate}
                    onpointerleave={() => (hovered = null)}
                >
                    {#if dataQuery?.error}
                        <EmptyState
                            compact
                            tone="danger"
                            title="Couldn't load emojis"
                            text="Check your connection and try again."
                            retry={() => attempt++}
                        />
                    {:else if !data || !customsSettled}
                        <div aria-hidden="true" class="flex flex-col gap-2">
                            <div class="h-4 w-32 skeleton rounded-md"></div>
                            <div class="grid gap-2" style:grid-template-columns="repeat({cols}, minmax(0, 1fr))">
                                {#each { length: cols * 5 } as _, index (index)}
                                    <div class="aspect-square skeleton rounded-xl"></div>
                                {/each}
                            </div>
                        </div>
                    {:else if query && !results.length}
                        <EmptyState
                            compact
                            icon={MaterialSymbolsSearchOffRounded}
                            title="No emoji found"
                            text="Try another name, like “smile” or “thumbsup”."
                        />
                    {:else}
                        {#each sections as section, s (section.key)}
                            <section
                                data-section={section.key}
                                class="pb-2 [content-visibility:auto]"
                                style:contain-intrinsic-size="auto {HEADER + Math.ceil(Math.max(section.cells.length, 1) / cols) * CELL + 8}px"
                            >
                                <h3 class={["sticky top-0 z-10 flex h-8 items-center gap-2 px-2 text-xs font-semibold text-gray-400", surface]}>
                                    {section.name}
                                </h3>
                                {#if section.key === "server" && customQuery?.error}
                                    <EmptyState
                                        compact
                                        tone="danger"
                                        title="Couldn't load server emojis"
                                        text="Square didn't answer. Try again in a moment."
                                        retry={() => customQuery?.refresh()}
                                    />
                                {:else}
                                    <div
                                        data-grid
                                        role="listbox"
                                        aria-label={section.name}
                                        class="grid"
                                        style:grid-template-columns="repeat({cols}, minmax(0, 1fr))"
                                    >
                                        {#each section.cells as cell, c (cell.key)}
                                            {@const id = `${section.key}/${cell.key}`}
                                            <button
                                                type="button"
                                                role="option"
                                                aria-selected="false"
                                                aria-disabled={!usable(cell) || undefined}
                                                data-cell
                                                tabindex={(roving ? roving === id : s === 0 && c === 0) ? 0 : -1}
                                                class={[
                                                    "flex h-10 items-center justify-center rounded-xl outline-none hover:bg-white/10 focus-visible:bg-white/10 focus-visible:ring-2 focus-visible:ring-accent/60 focus-visible:ring-inset",
                                                    !usable(cell) && "cursor-not-allowed",
                                                ]}
                                                onpointerenter={() => (hovered = cell)}
                                                onfocus={() => ((hovered = cell), (roving = id))}
                                                onclick={(event) => pick(cell, event.shiftKey)}
                                                onkeydown={(event) => {
                                                    if (event.key !== "Enter" || !event.shiftKey) return;
                                                    event.preventDefault();
                                                    pick(cell, true);
                                                }}
                                            >
                                                {@render glyph(cell)}
                                            </button>
                                        {/each}
                                    </div>
                                {/if}
                            </section>
                        {/each}
                    {/if}
                </div>
                <OverlayScrollbar viewport={scroller} inset={0} />
            </div>

            {#if !mobile.current}
                <div class="flex h-12 shrink-0 items-center gap-4 rounded-2xl bg-gray-900 px-4">
                    {#if preview}
                        {@render glyph(preview, true)}
                        <span class="flex min-w-0 flex-1 flex-col">
                            <span class="truncate text-sm font-medium">
                                :{preview.kind === "custom" ? preview.emoji.name : shortcodeOf(preview.emoji)}:
                            </span>
                            <span class="truncate text-xs text-gray-400">
                                {#if preview.kind === "unicode"}
                                    {preview.emoji[1]}
                                {:else if !preview.emoji.usable}
                                    Square can't use this emoji here
                                {:else}
                                    {preview.emoji.animated ? "Animated emoji" : "Emoji"} from {guild?.name}
                                {/if}
                            </span>
                        </span>
                    {:else}
                        <span class="text-xs text-gray-400">Hold Shift to pick more than one</span>
                    {/if}
                </div>
            {/if}
        </div>
    </Popup>
</Tooltip>
