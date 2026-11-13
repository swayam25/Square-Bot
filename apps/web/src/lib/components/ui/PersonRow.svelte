<script lang="ts">
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import type { Snippet } from "svelte";

    let {
        person,
        label,
        detail,
        children,
    }: {
        person: { name: string; avatarUrl: string | null } | null | undefined;
        label?: string;
        detail?: string;
        children?: Snippet;
    } = $props();
</script>

<div class="flex min-h-12 items-center gap-4 rounded-2xl bg-surface-2 p-2">
    {#if person}
        <Avatar src={person.avatarUrl} name={person.name} class="size-8" />
    {:else}
        <span class="size-8 shrink-0 rounded-full bg-white/5"></span>
    {/if}
    <span class="flex min-w-0 flex-1 flex-col">
        {#if label}<span class="text-xs text-gray-400">{label}</span>{/if}
        <span class="truncate text-sm font-medium">{person?.name ?? "Nobody"}</span>
        {#if detail}<span class="text-xs text-gray-400">{detail}</span>{/if}
    </span>
    {@render children?.()}
</div>
