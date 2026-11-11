<script module lang="ts">
    import type { Component } from "svelte";

    export type Option = { value: string; label: string; icon?: Component; hint?: string };
</script>

<script lang="ts">
    import Drawer from "#lib/components/ui/Drawer.svelte";
    import Input, { field, fieldText } from "#lib/components/ui/Input.svelte";
    import Portal from "#lib/components/ui/Portal.svelte";
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
        options,
        title,
        placeholder = "Select",
        disabled = false,
        invalid = false,
        class: className,
    }: {
        value?: string | null;
        options: Option[];
        title: string;
        placeholder?: string;
        disabled?: boolean;
        invalid?: boolean;
        class?: ClassValue;
    } = $props();

    let open = $state(false);
    let search = $state("");

    const selected = $derived(options.find((option) => option.value === value));
    const query = $derived(search.trim().toLowerCase());
    const filtered = $derived(
        open && query ? options.filter((option) => `${option.label} ${option.hint ?? ""}`.toLowerCase().includes(query)) : options,
    );
    const collection = $derived(
        createListCollection({ items: filtered, itemToString: (option) => option.label, itemToValue: (option) => option.value }),
    );

    function pick(next: string) {
        value = next;
        open = false;
        search = "";
    }
</script>

{#snippet label(option: Option)}
    {#if option.icon}<option.icon class="size-5 shrink-0 text-mist-400" />{/if}
    <span class="min-w-0 flex-1 truncate">{option.label}</span>
    {#if option.hint}<span class="shrink-0 font-mono text-xs text-mist-400">{option.hint}</span>{/if}
{/snippet}

{#if mobile.current}
    <div class={className}>
        <Drawer bind:open {title} triggerClass={[field, "pr-2 text-left", disabled && "pointer-events-none opacity-50"]}>
            {#snippet trigger()}
                {#if selected?.icon}<selected.icon class="size-5 shrink-0 text-mist-400" />{/if}
                <span class={["min-w-0 flex-1 truncate", !selected && "text-mist-400"]}>{selected?.label ?? placeholder}</span>
                <MaterialSymbolsKeyboardArrowDownRounded class="size-6 shrink-0 text-mist-400" />
            {/snippet}
            <div class="flex flex-col gap-4">
                <Input type="search" icon={MaterialSymbolsSearchRounded} placeholder="Search" aria-label="Search {title}" bind:value={search} />
                <div role="listbox" aria-label={title} class="flex flex-col gap-1">
                    {#each filtered as option (option.value)}
                        <button
                            type="button"
                            role="option"
                            aria-selected={option.value === value}
                            class="ripple flex h-12 shrink-0 items-center gap-4 rounded-2xl px-4 text-left text-sm font-medium hover:bg-white/10 aria-selected:bg-accent/10 aria-selected:text-accent"
                            {@attach ripple}
                            onclick={() => pick(option.value)}
                        >
                            {@render label(option)}
                        </button>
                    {:else}
                        <p class="px-4 py-2 text-sm text-mist-400">No matches</p>
                    {/each}
                </div>
            </div>
        </Drawer>
    </div>
{:else}
    <Combobox.Root
        {collection}
        value={value ? [value] : []}
        onValueChange={(details) => (value = details.value[0] ?? null)}
        bind:open
        inputValue={open ? search : (selected?.label ?? "")}
        onInputValueChange={(details) => details.reason === "input-change" && (search = details.inputValue)}
        onOpenChange={() => (search = "")}
        openOnClick
        inputBehavior="autohighlight"
        positioning={{ sameWidth: true, gutter: 8 }}
        {disabled}
        {invalid}
        class={className}
    >
        <Combobox.Control class={[field, "cursor-pointer pr-2"]}>
            {#if selected?.icon && !open}<selected.icon class="size-5 shrink-0 text-mist-400" />{/if}
            <Combobox.Input
                aria-label={title}
                placeholder={open && selected ? selected.label : placeholder}
                class={[fieldText, "h-full", !open && "cursor-pointer"]}
            />
            <Combobox.Trigger class="flex size-6 shrink-0 items-center justify-center text-mist-400">
                <MaterialSymbolsKeyboardArrowDownRounded class={["size-6 transition-transform duration-200", open && "rotate-180"]} />
            </Combobox.Trigger>
        </Combobox.Control>
        <Portal>
            <Combobox.Positioner class="z-50">
                <Combobox.Content
                    class="max-h-72 origin-(--transform-origin) overflow-y-auto overscroll-contain rounded-2xl bg-surface-2 p-2 shadow-2xl shadow-black/50 outline-none data-[state=closed]:animate-pop-out data-[state=open]:animate-pop-in"
                >
                    {#each collection.items as option (option.value)}
                        <Combobox.Item
                            item={option}
                            class="flex h-10 cursor-pointer items-center gap-4 rounded-xl px-4 text-sm font-medium data-highlighted:bg-white/10 data-[state=checked]:text-accent"
                        >
                            {@render label(option)}
                            <Combobox.ItemIndicator><MaterialSymbolsCheckRounded class="size-5" /></Combobox.ItemIndicator>
                        </Combobox.Item>
                    {:else}
                        <p class="px-4 py-2 text-sm text-mist-400">No matches</p>
                    {/each}
                </Combobox.Content>
            </Combobox.Positioner>
        </Portal>
    </Combobox.Root>
{/if}
