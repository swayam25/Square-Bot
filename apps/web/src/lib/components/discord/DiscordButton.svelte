<script lang="ts">
    import type { Snippet } from "svelte";

    type Style = "primary" | "secondary" | "success" | "danger";

    let { style = "secondary", href, disabled = false, children }: { style?: Style; href?: string; disabled?: boolean; children: Snippet } = $props();

    const styles: Record<Style, string> = {
        primary: "bg-dc-blurple hover:bg-[#4752c4]",
        secondary: "border border-[#97979f]/4 bg-[#97979f]/12 hover:bg-[#97979f]/20",
        success: "bg-dc-green hover:bg-[#047e37]",
        danger: "bg-dc-red hover:bg-[#b42831]",
    };
    const classes = $derived([
        "inline-flex h-8 min-w-15 items-center justify-center gap-2 rounded-lg px-4 py-0.5 text-sm font-medium whitespace-nowrap text-white transition-colors select-none",
        styles[href ? "secondary" : style],
        disabled && "pointer-events-none opacity-50",
    ]);
</script>

{#snippet external()}
    <svg viewBox="0 0 24 24" aria-hidden="true" class="size-4 fill-none stroke-current stroke-2 [stroke-linecap:round] [stroke-linejoin:round]">
        <path d="M14 4h6v6m0-6-9 9m7 1v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4" />
    </svg>
{/snippet}

<!-- Only link buttons do anything: the rest are a picture of a button, since their action lives in Discord -->
{#if href && URL.canParse(href) && /^https?:$/.test(new URL(href).protocol)}
    <a {href} target="_blank" rel="noopener noreferrer" class={classes}>{@render children()}{@render external()}</a>
{:else}
    <span class={classes}
        >{@render children()}{#if href !== undefined}{@render external()}{/if}</span
    >
{/if}
