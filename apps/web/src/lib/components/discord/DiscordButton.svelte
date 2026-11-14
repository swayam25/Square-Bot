<script lang="ts">
    import type { Snippet } from "svelte";
    import MaterialSymbolsOpenInNewRounded from "~icons/material-symbols/open-in-new-rounded";

    type Style = "primary" | "secondary" | "success" | "danger";

    let { style = "secondary", href, disabled = false, children }: { style?: Style; href?: string; disabled?: boolean; children: Snippet } = $props();

    const styles: Record<Style, [string, string]> = {
        primary: ["bg-dc-blurple", "hover:bg-dc-blurple-hover"],
        secondary: ["border border-dc-secondary/4 bg-dc-secondary/12", "hover:bg-dc-secondary/20"],
        success: ["bg-dc-green", "hover:bg-dc-green-hover"],
        danger: ["bg-dc-red", "hover:bg-dc-red-hover"],
    };
    const [fill, hover] = $derived(styles[href ? "secondary" : style]);
    const classes = $derived([
        "inline-flex h-8 min-w-15 items-center justify-center gap-2 rounded-lg px-4 py-0.5 text-sm font-medium whitespace-nowrap text-white transition-colors select-none",
        fill,
        disabled ? "cursor-not-allowed opacity-50" : ["cursor-pointer", hover],
    ]);
</script>

{#snippet external()}
    <MaterialSymbolsOpenInNewRounded aria-hidden="true" class="size-4" />
{/snippet}

<!-- Only link buttons do anything: the rest are a picture of a button, since their action lives in Discord -->
{#if href && URL.canParse(href) && /^https?:$/.test(new URL(href).protocol)}
    <a {href} target="_blank" rel="noopener noreferrer" class={classes}>{@render children()}{@render external()}</a>
{:else}
    <span class={classes}
        >{@render children()}{#if href !== undefined}{@render external()}{/if}</span
    >
{/if}
