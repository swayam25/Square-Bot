<script lang="ts">
    import Button from "#lib/components/ui/Button.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import type { Snippet } from "svelte";
    import type { ClassValue } from "svelte/elements";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";

    export type Tone = "neutral" | "muted" | "on" | "accent" | "success" | "warning" | "danger" | "violet";

    let {
        tone = "neutral",
        size = "md",
        remove,
        class: className,
        children,
    }: {
        tone?: Tone;
        size?: "sm" | "md";
        remove?: { label: string; onclick: () => void; disabled?: boolean };
        class?: ClassValue;
        children: Snippet;
    } = $props();

    const tones: Record<Tone, string> = {
        neutral: "bg-white/10 text-gray-100",
        muted: "bg-white/10 text-gray-400",
        on: "bg-accent/20 text-cyan-300",
        accent: "bg-accent/10 text-accent",
        success: "bg-emerald-400/10 text-emerald-400",
        warning: "bg-amber-400/10 text-amber-400",
        danger: "bg-red-400/10 text-red-400",
        violet: "bg-violet-500/20 text-violet-300",
    };
</script>

<span
    class={[
        "inline-flex shrink-0 items-center rounded-full font-medium whitespace-nowrap",
        size === "sm" ? "h-5 gap-1 px-2 text-2xs [&_svg]:size-3" : "h-8 gap-2 px-4 text-xs has-[svg]:px-3 [&_svg]:size-4",
        remove && "pr-1!",
        tones[tone],
        className,
    ]}
>
    {@render children()}
    {#if remove}
        <Tooltip content={remove.label}>
            <Button variant="ghost" size="xs" icon disabled={remove.disabled} onclick={remove.onclick}><MaterialSymbolsCloseRounded /></Button>
        </Tooltip>
    {/if}
</span>
