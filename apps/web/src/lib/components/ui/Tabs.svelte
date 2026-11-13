<script lang="ts" generics="T extends string">
    import { formatCount } from "#lib/format.ts";
    import { Tabs } from "@ark-ui/svelte/tabs";
    import type { Component, Snippet } from "svelte";

    let {
        tabs,
        value = $bindable(),
        label,
        children,
    }: {
        tabs: { value: T; label: string; icon?: Component; count?: number }[];
        value: T;
        label: string;
        children: Snippet;
    } = $props();
</script>

<Tabs.Root {value} onValueChange={(details) => (value = details.value as T)} class="flex flex-col gap-6">
    <Tabs.List aria-label={label} class="relative flex scrollbar-none gap-2 overflow-x-auto border-b border-white/10">
        {#each tabs as tab (tab.value)}
            <Tabs.Trigger
                value={tab.value}
                class="flex h-12 shrink-0 items-center gap-2 rounded-t-xl px-4 text-sm font-medium whitespace-nowrap text-gray-400 transition-colors hover:text-gray-100 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent data-selected:text-gray-50 md:h-10 [&_svg]:size-5"
            >
                {#if tab.icon}<tab.icon />{/if}
                {tab.label}
                {#if tab.count !== undefined}
                    <span class="rounded-full bg-white/10 px-2 font-mono text-2xs text-gray-400">{formatCount(tab.count)}</span>
                {/if}
            </Tabs.Trigger>
        {/each}
        <Tabs.Indicator class="bottom-0 h-0.5 w-(--width) rounded-full bg-accent" />
    </Tabs.List>
    <Tabs.Content {value} class="outline-none">{@render children()}</Tabs.Content>
</Tabs.Root>
