<script lang="ts">
    import loading from "#lib/assets/loading.svg";
    import { navigating, page } from "$app/state";
    import { onMount } from "svelte";
    import { fade } from "svelte/transition";

    const DELAY_MS = 400;
    const MIN_SHOWN_MS = 800;
    const BOOT_LIMIT_MS = 3_000;

    let navigatingSlowly = $state(false);
    let booting = $state(true);

    onMount(() => {
        const streamed = Object.values(page.data).filter((value) => value instanceof Promise);
        const limit = new Promise((resolve) => setTimeout(resolve, BOOT_LIMIT_MS));
        void Promise.race([Promise.allSettled([document.fonts.ready, ...streamed]), limit]).then(() => (booting = false));
    });

    $effect(() => {
        if (!navigating.to) return;
        let shownAt = 0;
        const show = setTimeout(() => {
            navigatingSlowly = true;
            shownAt = performance.now();
        }, DELAY_MS);
        return () => {
            clearTimeout(show);
            if (!shownAt) return;
            setTimeout(() => (navigatingSlowly = false), Math.max(0, MIN_SHOWN_MS - (performance.now() - shownAt)));
        };
    });
</script>

<svelte:head>
    <noscript>
        <style>
            [data-loader] {
                display: none;
            }
        </style>
    </noscript>
</svelte:head>

{#if booting || navigatingSlowly}
    <div
        data-loader
        role="status"
        aria-label="Loading"
        class="fixed inset-0 z-50 flex items-center justify-center bg-gray-950"
        in:fade={{ duration: 200 }}
        out:fade={{ duration: 400 }}
    >
        <img src={loading} alt="" fetchpriority="high" class="size-24" />
    </div>
{/if}
