<script lang="ts">
    import MaterialSymbolsKeyboardArrowDownRounded from "~icons/material-symbols/keyboard-arrow-down-rounded";

    let { label, placeholder = false, disabled = false }: { label: string; placeholder?: boolean; disabled?: boolean } = $props();
</script>

<div
    class={[
        "flex min-h-10 w-full max-w-100 items-center justify-between gap-2 rounded-lg border border-dc-border bg-dc-bg py-2 pr-2 pl-3 text-sm",
        placeholder && "text-dc-muted",
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
    ]}
>
    <span class="truncate">{label}</span>
    <MaterialSymbolsKeyboardArrowDownRounded aria-hidden="true" class="size-6 shrink-0 text-dc-icon" />
</div>
