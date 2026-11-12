<script lang="ts">
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import Dialog from "#lib/components/ui/Dialog.svelte";
    import { ripple } from "#lib/motion.ts";
    import { page } from "$app/state";
    import type { Person } from "@square/api-client";
    import MaterialSymbolsHeadphonesRounded from "~icons/material-symbols/headphones-rounded";

    let { listeners }: { listeners: Person[] } = $props();

    let open = $state(false);
    const STACK = 3;
    const me = $derived(page.data.user?.id);
    const label = $derived(listeners.length === 1 ? "1 listening" : `${listeners.length} listening`);
</script>

{#if listeners.length}
    <button
        type="button"
        aria-label="{label}, see who"
        aria-haspopup="dialog"
        class="ripple flex h-10 min-w-0 items-center gap-2 rounded-full bg-black/30 pr-4 pl-1 text-sm font-semibold backdrop-blur-xl transition-colors hover:bg-black/50"
        {@attach ripple}
        onclick={() => (open = true)}
    >
        <span class="flex shrink-0 -space-x-2">
            {#each listeners.slice(0, STACK) as person, i (person.id)}
                <Avatar
                    src={person.avatarUrl}
                    name={person.name}
                    class={["size-8 text-xs", i < Math.min(listeners.length, STACK) - 1 && "stack-bite"]}
                />
            {/each}
        </span>
        <MaterialSymbolsHeadphonesRounded class="size-4 shrink-0 text-mist-400" />
        <span class="truncate tabular-nums">{listeners.length}</span>
    </button>
{/if}

<Dialog
    bind:open
    title="Listening now"
    description={listeners.length
        ? `${listeners.length} ${listeners.length === 1 ? "person" : "people"} in Square's voice channel`
        : "Nobody is in the voice channel"}
>
    <ul class="flex flex-col gap-1">
        {#each listeners as person (person.id)}
            <li class="flex h-14 items-center gap-4 rounded-2xl px-2">
                <Avatar src={person.avatarUrl} name={person.name} class="size-10 text-sm" />
                <span class="min-w-0 flex-1 truncate font-medium">{person.name}</span>
                {#if person.id === me}<Chip tone="accent">You</Chip>{/if}
            </li>
        {/each}
    </ul>
</Dialog>

<style>
    :global(.stack-bite) {
        mask-image: radial-gradient(circle 1.125rem at calc(100% + 0.5rem) 50%, transparent 98%, #000);
    }
</style>
