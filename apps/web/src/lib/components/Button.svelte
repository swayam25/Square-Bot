<script lang="ts">
    import { ripple } from "#lib/motion.ts";
    import type { ClassValue, HTMLAnchorAttributes, HTMLButtonAttributes } from "svelte/elements";

    type Variant = "primary" | "secondary" | "danger" | "ghost";
    type Props = { variant?: Variant; size?: "md" | "lg"; icon?: boolean; class?: ClassValue } & (
        (HTMLButtonAttributes & { href?: undefined }) | (HTMLAnchorAttributes & { href: string })
    );

    let { variant = "secondary", size = "md", icon = false, class: className, children, ...rest }: Props = $props();

    const variants: Record<Variant, string> = {
        primary: "bg-accent font-semibold text-cyan-950 hover:bg-cyan-300",
        secondary: "bg-surface-2 font-medium hover:bg-surface-3",
        danger: "bg-red-400/10 font-medium text-red-400 hover:bg-red-400/20",
        ghost: "font-medium text-mist-400 hover:bg-surface-2 hover:text-mist-100",
    };

    // Taller on phones, where a 40px target is a miss waiting to happen
    const classes = $derived([
        "ripple inline-flex shrink-0 items-center justify-center gap-2 rounded-full text-sm whitespace-nowrap select-none",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:pointer-events-none disabled:opacity-50",
        icon
            ? "size-12 md:size-10 [&_svg]:size-5"
            : size === "lg"
              ? "h-12 px-6 text-base [&_svg]:size-5"
              : "h-12 px-6 md:h-10 md:px-4 [&_svg]:size-4",
        variants[variant],
        className,
    ]);
</script>

{#if rest.href !== undefined}
    <a {...rest as HTMLAnchorAttributes} class={classes} {@attach ripple}>{@render children?.()}</a>
{:else}
    <button type="button" {...rest as HTMLButtonAttributes} class={classes} {@attach ripple}>{@render children?.()}</button>
{/if}
