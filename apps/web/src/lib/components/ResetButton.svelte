<script lang="ts" generics="T">
    import ConfirmDialog from "#lib/components/ConfirmDialog.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import type { Component } from "svelte";
    import MaterialSymbolsReplayRounded from "~icons/material-symbols/replay-rounded";

    let {
        title,
        description,
        label = "Reset",
        busy = "Resetting…",
        variant = "secondary",
        done,
        icon: Icon = MaterialSymbolsReplayRounded,
        disabled = false,
        reset,
        apply,
    }: {
        title: string;
        description: string;
        label?: string;
        busy?: string;
        variant?: "secondary" | "danger";
        done: string;
        icon?: Component;
        disabled?: boolean;
        reset: () => Promise<T>;
        apply?: (result: T) => void;
    } = $props();

    let open = $state(false);
</script>

<Button {variant} {disabled} onclick={() => (open = true)}><Icon />{label}</Button>
<ConfirmDialog bind:open {title} {description} {label} {busy} {done} run={reset} {apply} />
