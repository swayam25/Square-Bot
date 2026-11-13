<script module lang="ts">
    // The bot's image cards pick a fallback pastel with `crc32(name) % 8`, so the same person gets the same color here
    const PASTELS = ["bg-amber-400", "bg-blue-300", "bg-rose-300", "bg-emerald-200", "bg-violet-200", "bg-orange-200", "bg-sky-200", "bg-pink-200"];

    const TABLE = Array.from({ length: 256 }, (_, n) => {
        let c = n;
        for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
        return c >>> 0;
    });

    function crc32(text: string) {
        let crc = 0xffffffff;
        for (const byte of new TextEncoder().encode(text)) crc = TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
        return (crc ^ 0xffffffff) >>> 0;
    }

    function initial(name: string) {
        return (
            name
                .normalize("NFKC")
                .match(/[\p{L}\p{N}]/u)?.[0]
                .toUpperCase() ?? "?"
        );
    }
</script>

<script lang="ts">
    import Picture from "#lib/components/ui/Picture.svelte";
    import type { ClassValue } from "svelte/elements";

    let { src, name, class: className = "size-10", animate }: { src?: string | null; name: string; class?: ClassValue; animate?: boolean } = $props();
</script>

<Picture {src} alt={name} {animate} class={["rounded-full", className]}>
    {#snippet fallback({ loading })}
        <span
            class={[
                "flex size-full items-center justify-center font-semibold text-gray-950",
                loading ? "skeleton" : PASTELS[crc32(name) % PASTELS.length],
            ]}
        >
            {#if !loading}{initial(name)}{/if}
        </span>
    {/snippet}
</Picture>
