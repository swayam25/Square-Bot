<script lang="ts">
    import type { ClassValue } from "svelte/elements";
    import MaterialSymbolsMusicNoteRounded from "~icons/material-symbols/music-note-rounded";

    let { src, class: className, lazy = false }: { src: string | null | undefined; class?: ClassValue; lazy?: boolean } = $props();

    let broken = $derived.by(() => (void src, false));
</script>

{#if src && !broken}
    <!-- Google's image host answers 429 to hotlinks that carry a Referer, which is why Discord shows covers we didn't -->
    <img
        {src}
        alt=""
        draggable="false"
        referrerpolicy="no-referrer"
        loading={lazy ? "lazy" : undefined}
        onerror={() => (broken = true)}
        class={["shrink-0 bg-surface-2 object-cover", className]}
    />
{:else}
    <span class={["flex shrink-0 items-center justify-center bg-surface-2 text-gray-400", className]}>
        <MaterialSymbolsMusicNoteRounded class="size-1/2" />
    </span>
{/if}
