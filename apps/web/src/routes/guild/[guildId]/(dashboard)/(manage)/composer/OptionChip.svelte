<script lang="ts">
    import { ripple } from "#lib/attachments/ripple.ts";
    import { focusRing } from "#lib/components/ui/styles.ts";
    import type { Component, Snippet } from "svelte";

    let { pressed = $bindable(false), icon: Icon, children }: { pressed?: boolean; icon: Component; children: Snippet } = $props();
</script>

<button
    type="button"
    aria-pressed={pressed}
    class={[
        "ripple flex h-8 shrink-0 items-center gap-2 rounded-full px-3 text-xs font-medium whitespace-nowrap transition-colors [&>svg]:size-4",
        pressed ? "bg-accent/10 text-accent" : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-100",
        focusRing,
    ]}
    {@attach ripple}
    onclick={() => (pressed = !pressed)}
>
    <Icon />
    {@render children()}
</button>
