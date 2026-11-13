<script lang="ts">
    import type { Snippet } from "svelte";
    import type { ClassValue } from "svelte/elements";

    let { color, class: className, children }: { color?: string | null; class?: ClassValue; children: Snippet } = $props();
</script>

<div
    style:border-left-color={color || undefined}
    class={[
        "flex w-full max-w-150 flex-col gap-2 rounded-lg border border-dc-border bg-dc-surface p-4 [&_pre]:max-w-full",
        color && "border-l-4",
        className,
    ]}
>
    {@render children()}
</div>
