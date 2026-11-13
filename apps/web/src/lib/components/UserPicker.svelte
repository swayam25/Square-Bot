<script lang="ts">
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import Drawer from "#lib/components/ui/Drawer.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import OverlayScrollbar from "#lib/components/ui/OverlayScrollbar.svelte";
    import Portal from "#lib/components/ui/Portal.svelte";
    import { field, fieldText, menuItem, menuNote, menuPanel, sheetItem } from "#lib/components/ui/styles.ts";
    import { Debounced } from "#lib/debounced.svelte.ts";
    import { mobile } from "#lib/media.ts";
    import { ripple } from "#lib/motion.ts";
    import * as settings from "#lib/settings.remote.ts";
    import { createListCollection } from "@ark-ui/svelte/collection";
    import { Combobox } from "@ark-ui/svelte/combobox";
    import type { UserMatch } from "@square/api-client";
    import type { ClassValue } from "svelte/elements";
    import MaterialSymbolsSearchRounded from "~icons/material-symbols/search-rounded";

    let {
        guild,
        title,
        exclude = [],
        humansOnly = false,
        disabled = false,
        placeholder = "Add a person",
        onpick,
        class: className,
    }: {
        guild: string;
        title: string;
        exclude?: string[];
        humansOnly?: boolean;
        disabled?: boolean;
        placeholder?: string;
        onpick: (user: UserMatch) => void;
        class?: ClassValue;
    } = $props();

    let open = $state(false);
    let menu = $state<HTMLElement | null>(null);
    let typed = $state("");
    const debounced = new Debounced(() => typed.trim(), 250);
    const search = $derived(debounced.current);

    $effect(() => {
        if (!open) typed = "";
    });

    const results = $derived(search ? settings.searchMembers({ guild, q: search }) : null);
    const found = $derived((results?.current ?? []).filter((user) => !exclude.includes(user.id) && !(humansOnly && user.bot)));
    const busy = $derived(results?.loading || typed.trim() !== search);
    const collection = $derived(createListCollection({ items: found, itemToString: (user) => user.name, itemToValue: (user) => user.id }));

    function pick(user: UserMatch) {
        onpick(user);
        open = false;
    }
</script>

{#snippet userRow(user: UserMatch)}
    <Avatar src={user.avatarUrl} name={user.name} class="size-8 md:size-6" />
    <span class="flex min-w-0 flex-1 flex-col md:flex-row md:items-baseline md:gap-2">
        <span class="truncate">{user.name}</span>
        <span class="truncate text-xs font-normal text-gray-400">@{user.username}</span>
    </span>
    {#if user.bot}<Chip tone="violet" size="sm">Bot</Chip>{/if}
    {#if !user.member}<Chip tone="muted" size="sm">Not in server</Chip>{/if}
{/snippet}

{#snippet status()}
    {#if !search}
        <p class={menuNote}>Type a name, or paste a user ID for someone who hasn't joined yet.</p>
    {:else if results?.error}
        <EmptyState
            tone="danger"
            compact
            title="Couldn't search"
            text={results.error.message ?? "Square didn't answer. Try again in a moment."}
            retry={() => results.refresh()}
        />
    {:else if !results?.current}
        {#each [0, 1, 2] as row (row)}
            <div class="h-12 skeleton rounded-2xl md:h-10 md:rounded-xl"></div>
        {/each}
    {:else if !found.length}
        <p class={menuNote}>No one matches that.</p>
    {/if}
{/snippet}

{#if mobile.current}
    <Drawer bind:open {title} triggerClass={[field, "text-left", disabled && "pointer-events-none opacity-50", className]}>
        {#snippet trigger()}
            <MaterialSymbolsSearchRounded />
            <span class="min-w-0 flex-1 truncate text-gray-400">{placeholder}</span>
        {/snippet}
        <div class="flex flex-col gap-4">
            <Input type="search" icon={MaterialSymbolsSearchRounded} placeholder="Name or user ID" aria-label="Search people" bind:value={typed} />
            <div role="listbox" aria-label={title} aria-busy={busy} class="flex flex-col gap-1">
                {#each found as user (user.id)}
                    <button type="button" role="option" aria-selected="false" class={sheetItem} {@attach ripple} onclick={() => pick(user)}>
                        {@render userRow(user)}
                    </button>
                {/each}
                {@render status()}
            </div>
        </div>
    </Drawer>
{:else}
    <Combobox.Root
        {collection}
        value={[]}
        bind:open
        inputValue={typed}
        onInputValueChange={(details) => details.reason === "input-change" && (typed = details.inputValue)}
        onValueChange={(details) => {
            const user = found.find((match) => match.id === details.value[0]);
            if (user) pick(user);
        }}
        openOnClick
        inputBehavior="autohighlight"
        selectionBehavior="clear"
        positioning={{ sameWidth: true, gutter: 8 }}
        {disabled}
        class={className}
    >
        <Combobox.Control class={[field, "pr-2"]}>
            <MaterialSymbolsSearchRounded />
            <Combobox.Input aria-label={title} {placeholder} class={[fieldText, "h-full"]} />
        </Combobox.Control>
        <Portal>
            <Combobox.Positioner class="z-50">
                <Combobox.Content bind:ref={menu} aria-busy={busy} class={menuPanel}>
                    {#each collection.items as user (user.id)}
                        <Combobox.Item item={user} class={menuItem}>{@render userRow(user)}</Combobox.Item>
                    {/each}
                    {@render status()}
                </Combobox.Content>
                <OverlayScrollbar viewport={menu} inset={8} />
            </Combobox.Positioner>
        </Portal>
    </Combobox.Root>
{/if}
