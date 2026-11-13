<script lang="ts">
    let { label }: { label: string } = $props();
</script>

<div
    role="separator"
    class="mx-4 mt-6 mb-2 flex items-center text-xs leading-3.25 font-semibold text-dc-muted before:h-px before:flex-1 before:bg-dc-line after:h-px after:flex-1 after:bg-dc-line"
>
    <span class="px-1">{label}</span>
</div>
