<script lang="ts">
    // Needs a `group/field relative` parent: shows while that field is hovered or focused
    let { id, error }: { id: string; error: string | null | undefined } = $props();
</script>

{#if error}
    <span
        {id}
        role="alert"
        class={[
            "pointer-events-none absolute top-full left-2 z-30 mt-2 w-max max-w-72 rounded-xl bg-red-400 px-4 py-2 text-xs font-medium text-red-950 shadow-xl shadow-black/50",
            "before:absolute before:-top-1 before:left-4 before:size-2 before:rotate-45 before:bg-red-400",
            "opacity-0 transition-opacity duration-150 ease-in",
            "group-focus-within/field:opacity-100 group-focus-within/field:duration-200 group-focus-within/field:ease-out group-hover/field:opacity-100 group-hover/field:duration-200 group-hover/field:ease-out",
        ]}
    >
        {error}
    </span>
{/if}
