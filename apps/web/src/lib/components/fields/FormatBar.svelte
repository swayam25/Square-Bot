<script lang="ts">
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import type { Format } from "#lib/discord/editor/format.ts";
    import type { Component } from "svelte";
    import MaterialSymbolsCodeRounded from "~icons/material-symbols/code-rounded";
    import MaterialSymbolsFormatBoldRounded from "~icons/material-symbols/format-bold-rounded";
    import MaterialSymbolsFormatItalicRounded from "~icons/material-symbols/format-italic-rounded";
    import MaterialSymbolsFormatQuoteRounded from "~icons/material-symbols/format-quote-rounded";
    import MaterialSymbolsFormatUnderlinedRounded from "~icons/material-symbols/format-underlined-rounded";
    import MaterialSymbolsStrikethroughSRounded from "~icons/material-symbols/strikethrough-s-rounded";
    import MaterialSymbolsVisibilityOffRounded from "~icons/material-symbols/visibility-off-rounded";

    let { active, onformat }: { active: Set<Format>; onformat: (format: Format) => void } = $props();

    const mod = /Mac|iPhone|iPad/.test(navigator.userAgent) ? "⌘" : "Ctrl+";

    const BUTTONS: { format: Format; label: string; icon: Component; key?: string }[] = [
        { format: "bold", label: "Bold", icon: MaterialSymbolsFormatBoldRounded, key: "B" },
        { format: "italic", label: "Italic", icon: MaterialSymbolsFormatItalicRounded, key: "I" },
        { format: "underline", label: "Underline", icon: MaterialSymbolsFormatUnderlinedRounded, key: "U" },
        { format: "strike", label: "Strikethrough", icon: MaterialSymbolsStrikethroughSRounded },
        { format: "spoiler", label: "Spoiler", icon: MaterialSymbolsVisibilityOffRounded },
        { format: "code", label: "Code", icon: MaterialSymbolsCodeRounded },
        { format: "quote", label: "Quote", icon: MaterialSymbolsFormatQuoteRounded },
    ];
</script>

<!-- Pressing a button mustn't take focus, or the selection it acts on would go -->
<div role="toolbar" aria-label="Formatting" class="flex animate-pop-in gap-0.5 rounded-2xl bg-gray-700 p-1 shadow-xl shadow-black/50">
    {#each BUTTONS as { format, label, icon: Icon, key } (format)}
        <Tooltip content={key ? `${label} (${mod}${key})` : label}>
            <button
                type="button"
                aria-pressed={active.has(format)}
                onpointerdown={(event) => event.preventDefault()}
                onclick={() => onformat(format)}
                class="grid size-8 place-items-center rounded-xl text-gray-300 transition-colors hover:bg-white/10 hover:text-gray-100 aria-pressed:bg-accent/15 aria-pressed:text-accent"
            >
                <Icon aria-hidden="true" class="size-5" />
            </button>
        </Tooltip>
    {/each}
</div>
