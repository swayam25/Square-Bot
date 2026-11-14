<script module lang="ts">
    function acronym(name: string) {
        return (
            name
                .replace(/'s /g, " ")
                .replace(/\w+/g, (word) => word[0])
                .replace(/\s/g, "") || "?"
        );
    }
</script>

<script lang="ts">
    import Picture from "#lib/components/ui/Picture.svelte";
    import type { ClassValue } from "svelte/elements";

    let {
        src,
        name,
        class: className = "size-12 rounded-2xl",
        animate,
    }: { src?: string | null; name: string; class?: ClassValue; animate?: boolean } = $props();

    const letters = $derived(acronym(name));
    const scale = $derived(letters.length <= 2 ? 38 : letters.length <= 4 ? 30 : 22);
</script>

<Picture {src} alt={name} {animate} class={["@container", className]}>
    {#snippet fallback({ loading })}
        <span
            class={["flex size-full items-center justify-center bg-gray-800 font-medium whitespace-nowrap", loading && "animate-pulse"]}
            style="font-size: {scale}cqw"
        >
            {#if !loading}{letters}{/if}
        </span>
    {/snippet}
</Picture>
