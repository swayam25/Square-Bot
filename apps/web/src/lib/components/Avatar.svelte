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

    // Same as the bot: NFKC folds styled letters like 𝓶 into plain ones
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
    import { Avatar } from "@ark-ui/svelte/avatar";
    import type { ClassValue } from "svelte/elements";

    let { src, name, class: className = "size-10" }: { src?: string | null; name: string; class?: ClassValue } = $props();

    let status = $state<"loading" | "loaded" | "error">("loading");
    $effect.pre(() => {
        void src;
        status = "loading";
    });
</script>

<Avatar.Root
    onStatusChange={(details) => (status = details.status)}
    class={["relative inline-flex shrink-0 overflow-hidden rounded-full", className]}
>
    <Avatar.Fallback
        class={[
            "flex size-full items-center justify-center font-semibold text-mist-950",
            src && status === "loading" ? "animate-pulse bg-surface-3" : PASTELS[crc32(name) % PASTELS.length],
        ]}
    >
        {#if !src || status === "error"}{initial(name)}{/if}
    </Avatar.Fallback>
    {#if src}
        <Avatar.Image {src} alt={name} class="size-full animate-fade-in object-cover" />
    {/if}
</Avatar.Root>
