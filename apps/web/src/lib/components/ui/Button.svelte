<script lang="ts">
    import { focusRing } from "#lib/components/ui/styles.ts";
    import { ripple } from "#lib/motion.ts";
    import type { ClassValue, HTMLAnchorAttributes, HTMLButtonAttributes } from "svelte/elements";
    import SvgSpinners90RingWithBg from "~icons/svg-spinners/90-ring-with-bg";

    type Variant = "primary" | "secondary" | "danger" | "ghost" | "ghost-danger";
    type Size = "xs" | "sm" | "md" | "lg";
    type Props = { variant?: Variant; size?: Size; icon?: boolean; loading?: boolean; class?: ClassValue } & (
        (HTMLButtonAttributes & { href?: undefined }) | (HTMLAnchorAttributes & { href: string })
    );

    let { variant = "secondary", size = "md", icon = false, loading = false, class: className, children, ...rest }: Props = $props();

    const variants: Record<Variant, string> = {
        primary: "bg-accent font-semibold text-cyan-950 hover:bg-cyan-300",
        secondary: "bg-gray-800 font-medium hover:bg-gray-700",
        danger: "bg-red-400/10 font-medium text-red-400 hover:bg-red-400/20",
        ghost: "font-medium text-gray-400 hover:bg-surface-2 hover:text-gray-100",
        // For a delete action that repeats down a list, where a red fill on every row would shout
        "ghost-danger": "font-medium text-gray-400 hover:bg-red-400/10 hover:text-red-400",
    };

    const iconSizes: Record<Size, string> = {
        xs: "size-8 md:size-6 [&_svg]:size-4",
        sm: "size-10 md:size-8 [&_svg]:size-5",
        md: "size-12 md:size-10 [&_svg]:size-5",
        lg: "size-12 [&_svg]:size-6",
    };
    const textSizes: Record<Size, string> = {
        xs: "h-8 px-3 text-xs md:h-6 [&_svg]:size-3",
        sm: "h-10 px-4 text-xs md:h-8 md:px-3 [&_svg]:size-4",
        md: "h-12 px-6 md:h-10 md:px-4 [&_svg]:size-4",
        lg: "h-12 px-6 text-base [&_svg]:size-5",
    };

    const classes = $derived([
        "ripple inline-flex shrink-0 items-center justify-center gap-2 rounded-full text-sm whitespace-nowrap select-none",
        focusRing,
        "disabled:pointer-events-none",
        !loading && "disabled:opacity-50",
        icon ? iconSizes[size] : textSizes[size],
        variants[variant],
        className,
    ]);
</script>

{#if rest.href !== undefined}
    <a {...rest as HTMLAnchorAttributes} class={classes} {@attach ripple}>{@render children?.()}</a>
{:else}
    <button
        type="button"
        {...rest as HTMLButtonAttributes}
        disabled={loading || (rest as HTMLButtonAttributes).disabled}
        aria-busy={loading || undefined}
        class={classes}
        {@attach ripple}
    >
        {#if loading}<SvgSpinners90RingWithBg />{/if}
        {#if !(loading && icon)}{@render children?.()}{/if}
    </button>
{/if}
