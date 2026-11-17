<script lang="ts">
    import { ripple } from "#lib/attachments/ripple.ts";
    import { focusRing } from "#lib/components/ui/styles.ts";
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
        ghost: "font-medium text-gray-400 hover:bg-gray-800 hover:text-gray-100",
        "ghost-danger": "font-medium text-gray-400 hover:bg-red-400/10 hover:text-red-400",
    };

    const shapes: Record<Size, string> = {
        xs: "rounded-xl md:rounded-lg [&_svg]:size-4.5 md:[&_svg]:size-4",
        sm: "rounded-2xl md:rounded-xl [&_svg]:size-5 md:[&_svg]:size-4.5",
        md: "rounded-control-lg md:rounded-2xl [&_svg]:size-5.5 md:[&_svg]:size-5",
        lg: "rounded-3xl md:rounded-control-lg [&_svg]:size-6",
    };
    const iconSizes: Record<Size, string> = {
        xs: "size-8 md:size-6",
        sm: "size-10 md:size-8",
        md: "size-12 md:size-10",
        lg: "size-14 md:size-12",
    };
    const textSizes: Record<Size, string> = {
        xs: "h-8 gap-1.5 px-3 text-[13px] md:h-6 md:gap-1 md:px-2 md:text-xs",
        sm: "h-10 px-3 md:h-8 md:gap-1.5 md:text-[13px]",
        md: "h-12 px-4 text-[15px] md:h-10 md:px-3 md:text-sm",
        lg: "h-14 px-4 text-base md:h-12",
    };

    const classes = $derived([
        "ripple inline-flex shrink-0 items-center justify-center gap-2 text-sm whitespace-nowrap select-none",
        focusRing,
        "disabled:pointer-events-none",
        !loading && "disabled:opacity-50",
        shapes[size],
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
