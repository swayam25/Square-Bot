<script lang="ts">
    import { Switch } from "@ark-ui/svelte/switch";
    import type { Snippet } from "svelte";

    let {
        checked = $bindable(false),
        disabled = false,
        label,
        children,
        onCheckedChange,
    }: {
        checked?: boolean;
        disabled?: boolean;
        label?: string;
        children?: Snippet;
        onCheckedChange?: (checked: boolean) => void;
    } = $props();
</script>

<Switch.Root
    bind:checked
    {disabled}
    onCheckedChange={(details) => onCheckedChange?.(details.checked)}
    class="group relative inline-flex cursor-pointer items-center gap-4 data-disabled:cursor-default data-disabled:opacity-50"
>
    <Switch.Control
        aria-label={children ? undefined : label}
        class="relative h-8 w-16 shrink-0 rounded-full bg-black/40 transition-colors duration-200 group-focus-visible:outline-2 group-focus-visible:outline-offset-2 group-focus-visible:outline-accent data-[state=checked]:bg-accent"
    >
        <Switch.Thumb
            class="absolute top-1 left-1 h-6 w-8 rounded-full bg-gray-400 shadow-md shadow-black/30 transition-[translate,width,background-color] duration-400 ease-spring group-active:w-10 data-[state=checked]:translate-x-6 data-[state=checked]:bg-gray-50 data-[state=checked]:group-active:translate-x-4"
        />
    </Switch.Control>
    {#if children}
        <Switch.Label class="text-sm">{@render children()}</Switch.Label>
    {/if}
    <Switch.HiddenInput />
</Switch.Root>
