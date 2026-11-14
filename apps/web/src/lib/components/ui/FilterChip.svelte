<script lang="ts">
    import { focusRing } from "#lib/components/ui/styles.ts";
    import { ripple } from "#lib/motion.ts";
    import type { Snippet } from "svelte";
    import type { ClassValue } from "svelte/elements";

    let { checked, onclick, class: className, children }: { checked: boolean; onclick: () => void; class?: ClassValue; children: Snippet } = $props();
</script>

<button
    type="button"
    role="radio"
    aria-checked={checked}
    class={[
        "ripple flex h-8 shrink-0 items-center gap-2 rounded-full px-3 text-xs font-medium whitespace-nowrap transition-colors [&>svg]:size-4",
        checked ? "bg-accent/10 text-accent" : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-100",
        focusRing,
        className,
    ]}
    {@attach ripple}
    {onclick}
>
    {@render children()}
</button>
