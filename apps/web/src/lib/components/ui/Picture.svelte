<script lang="ts">
    import { frames } from "#lib/animated.ts";
    import type { Snippet } from "svelte";
    import type { ClassValue } from "svelte/elements";

    let {
        src,
        alt,
        class: className,
        animate,
        fallback,
    }: {
        src?: string | null;
        alt: string;
        class?: ClassValue;
        animate?: boolean;
        fallback: Snippet<[{ loading: boolean }]>;
    } = $props();

    // Like Discord, an animated picture holds still until it's hovered. `animate` lets a parent row decide instead
    const parts = $derived(frames(src));
    const still = $derived(parts?.still ?? src);
    let hovered = $state(false);
    const playing = $derived(parts !== null && (animate ?? hovered));

    let status = $state<"loading" | "loaded" | "error">("loading");

    // A cached picture can finish before the load listener exists, so check once it's in the page and on every new src
    function settle(img: HTMLImageElement) {
        void still;
        status = img.complete ? (img.naturalWidth ? "loaded" : "error") : "loading";
    }
</script>

<span
    role="presentation"
    onpointerenter={() => (hovered = true)}
    onpointerleave={() => (hovered = false)}
    class={["relative inline-flex shrink-0 overflow-hidden", className]}
>
    {#if status !== "loaded"}
        {@render fallback({ loading: !!still && status === "loading" })}
    {/if}
    {#if still}
        <img
            src={still}
            {alt}
            hidden={status !== "loaded"}
            onload={() => (status = "loaded")}
            onerror={() => (status = "error")}
            {@attach settle}
            class="size-full animate-fade-in object-cover"
        />
    {/if}
    {#if playing && status === "loaded"}
        <img src={parts!.moving} alt="" class="absolute inset-0 size-full object-cover" />
    {/if}
</span>
