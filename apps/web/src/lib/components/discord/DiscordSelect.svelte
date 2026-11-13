<script lang="ts">
    let { label, placeholder = false, disabled = false }: { label: string; placeholder?: boolean; disabled?: boolean } = $props();
</script>

<div
    class={[
        "flex min-h-10 w-full max-w-100 items-center justify-between gap-2 rounded-lg border border-dc-border bg-dc-bg py-2 pr-2 pl-3 text-sm",
        placeholder && "text-dc-muted",
        disabled && "opacity-50",
    ]}
>
    <span class="truncate">{label}</span>
    <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        class="size-6 shrink-0 fill-none stroke-dc-icon stroke-2 [stroke-linecap:round] [stroke-linejoin:round]"
    >
        <path d="m6 9 6 6 6-6" />
    </svg>
</div>
