<script lang="ts">
    import type { Snippet } from "svelte";
    import type { ClassValue } from "svelte/elements";

    export type Tone = "neutral" | "muted" | "on" | "accent" | "success" | "warning" | "danger" | "violet";

    let { tone = "neutral", class: className, children }: { tone?: Tone; class?: ClassValue; children: Snippet } = $props();

    const tones: Record<Tone, string> = {
        neutral: "bg-white/10 text-mist-100",
        muted: "bg-white/10 text-mist-400",
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
        "inline-flex h-8 shrink-0 items-center gap-2 rounded-full px-4 text-xs font-medium whitespace-nowrap has-[svg]:px-3 [&_svg]:size-4",
        tones[tone],
        className,
    ]}
>
    {@render children()}
</span>
