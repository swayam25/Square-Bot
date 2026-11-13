<script module lang="ts">
    import type { Component } from "svelte";

    export type Option = { value: string; label: string; icon?: Component; color?: string; hint?: string };
</script>

<script lang="ts">
    import Chip from "#lib/components/ui/Chip.svelte";
    import Drawer from "#lib/components/ui/Drawer.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import OverlayScrollbar from "#lib/components/ui/OverlayScrollbar.svelte";
    import Portal from "#lib/components/ui/Portal.svelte";
    import ScrollRow from "#lib/components/ui/ScrollRow.svelte";
    import { field, fieldText, menuItem, menuNote, menuPanel, sheetItem } from "#lib/components/ui/styles.ts";
    import { mobile } from "#lib/media.ts";
    import { ripple } from "#lib/motion.ts";
    import { createListCollection } from "@ark-ui/svelte/collection";
    import { Combobox } from "@ark-ui/svelte/combobox";
    import type { ClassValue } from "svelte/elements";
    import MaterialSymbolsCheckRounded from "~icons/material-symbols/check-rounded";
    import MaterialSymbolsKeyboardArrowDownRounded from "~icons/material-symbols/keyboard-arrow-down-rounded";
    import MaterialSymbolsSearchRounded from "~icons/material-symbols/search-rounded";

    let {
        value = $bindable(null),
        values = $bindable([]),
        multiple = false,
        max = Infinity,
        options,
        title,
        placeholder = "Select",
        disabled = false,
        invalid = false,
        class: className,
    }: {
        value?: string | null;
        values?: string[];
        multiple?: boolean;
        max?: number;
        options: Option[];
        title: string;
        placeholder?: string;
        disabled?: boolean;
        invalid?: boolean;
        class?: ClassValue;
    } = $props();

    let open = $state(false);
    let menu = $state<HTMLElement | null>(null);
    let search = $state("");

    const selected = $derived(multiple ? undefined : options.find((option) => option.value === value));
    const chosen = $derived(multiple ? options.filter((option) => values.includes(option.value)) : []);
    const full = $derived(values.length >= max);
    const query = $derived(search.trim().toLowerCase());
    const filtered = $derived(
        open && query ? options.filter((option) => `${option.label} ${option.hint ?? ""}`.toLowerCase().includes(query)) : options,
    );
    const collection = $derived(
        createListCollection({
            items: filtered,
            itemToString: (option) => option.label,
            itemToValue: (option) => option.value,
            isItemDisabled: (option) => multiple && full && !values.includes(option.value),
        }),
    );

    function pick(next: string) {
        search = "";
        if (!multiple) {
            value = next;
            open = false;
        } else if (values.includes(next)) {
            values = values.filter((id) => id !== next);
        } else if (!full) {
            values = [...values, next];
        }
    }
</script>

{#snippet marker(option: Option)}
    {#if option.icon}
        <option.icon class="size-4 shrink-0 text-gray-400" />
    {:else if option.color}
        <!-- Fills the same box as the icon markers, minus the blank edge a glyph leaves -->
        <span class="size-4 shrink-0 p-0.5"><span class="block size-full rounded-full" style:background-color={option.color}></span></span>
    {/if}
{/snippet}

{#snippet label(option: Option)}
    {@render marker(option)}
    <span class="min-w-0 flex-1 truncate">{option.label}</span>
    {#if option.hint}<span class="shrink-0 font-mono text-xs text-gray-400">{option.hint}</span>{/if}
{/snippet}

<div class={["flex flex-col gap-2", className]}>
    {#if mobile.current}
        <Drawer bind:open {title} triggerClass={[field, "pr-2 text-left", disabled && "pointer-events-none opacity-50"]}>
            {#snippet trigger()}
                {#if selected}{@render marker(selected)}{/if}
                <span class={["min-w-0 flex-1 truncate", !selected && "text-gray-400"]}>{selected?.label ?? placeholder}</span>
                {#if multiple && max !== Infinity}<span class="shrink-0 font-mono text-xs text-gray-400">{values.length}/{max}</span>{/if}
                <MaterialSymbolsKeyboardArrowDownRounded class="size-5 shrink-0 text-gray-400" />
            {/snippet}
            <div class="flex flex-col gap-4">
                <Input type="search" icon={MaterialSymbolsSearchRounded} placeholder="Search" aria-label="Search {title}" bind:value={search} />
                <div role="listbox" aria-label={title} class="flex flex-col gap-1">
                    {#each filtered as option (option.value)}
                        <button
                            type="button"
                            role="option"
                            aria-selected={multiple ? values.includes(option.value) : option.value === value}
                            disabled={multiple && full && !values.includes(option.value)}
                            class={sheetItem}
                            {@attach ripple}
                            onclick={() => pick(option.value)}
                        >
                            {@render label(option)}
                        </button>
                    {:else}
                        <p class={menuNote}>No matches</p>
                    {/each}
                </div>
            </div>
        </Drawer>
    {:else}
        <Combobox.Root
            {collection}
            value={multiple ? values : value ? [value] : []}
            onValueChange={(details) => {
                if (multiple) {
                    values = details.value;
                    search = "";
                } else value = details.value[0] ?? null;
            }}
            {multiple}
            closeOnSelect={!multiple}
            bind:open
            inputValue={open ? search : (selected?.label ?? "")}
            onInputValueChange={(details) => details.reason === "input-change" && (search = details.inputValue)}
            onOpenChange={() => (search = "")}
            openOnClick
            inputBehavior="autohighlight"
            positioning={{ sameWidth: true, gutter: 8 }}
            {disabled}
            {invalid}
        >
            <Combobox.Control class={[field, "cursor-pointer pr-2"]}>
                {#if selected && !open}{@render marker(selected)}{/if}
                <Combobox.Input
                    aria-label={title}
                    placeholder={open && selected ? selected.label : placeholder}
                    class={[fieldText, "h-full", !open && "cursor-pointer"]}
                />
                {#if multiple && max !== Infinity}<span class="shrink-0 font-mono text-xs text-gray-400">{values.length}/{max}</span>{/if}
                <Combobox.Trigger class="flex size-6 shrink-0 items-center justify-center text-gray-400">
                    <MaterialSymbolsKeyboardArrowDownRounded class={["size-5 transition-transform duration-200", open && "rotate-180"]} />
                </Combobox.Trigger>
            </Combobox.Control>
            <Portal>
                <Combobox.Positioner class="z-50">
                    <Combobox.Content bind:ref={menu} class={menuPanel}>
                        {#each collection.items as option (option.value)}
                            <Combobox.Item item={option} class={menuItem}>
                                {@render label(option)}
                                <Combobox.ItemIndicator><MaterialSymbolsCheckRounded class="size-5" /></Combobox.ItemIndicator>
                            </Combobox.Item>
                        {:else}
                            <p class={menuNote}>No matches</p>
                        {/each}
                    </Combobox.Content>
                    <OverlayScrollbar viewport={menu} inset={8} />
                </Combobox.Positioner>
            </Portal>
        </Combobox.Root>
    {/if}
    {#if chosen.length}
        <ScrollRow as="ul" aria-label="Picked">
            {#each chosen as option (option.value)}
                <li>
                    <Chip
                        class="pl-3"
                        remove={{
                            label: `Remove ${option.label}`,
                            disabled,
                            onclick: () => (values = values.filter((id) => id !== option.value)),
                        }}
                    >
                        {@render marker(option)}
                        <span class="max-w-48 truncate">{option.label}</span>
                    </Chip>
                </li>
            {/each}
        </ScrollRow>
    {/if}
</div>
