<script lang="ts">
    import Logo from "#lib/components/Logo.svelte";
    import { navigating } from "$app/state";
    import { fade } from "svelte/transition";

    // Quick navigations finish before anyone notices; only a slow one gets the full-screen logo
    const DELAY_MS = 400;
    // Once shown, it stays long enough for one pass of the wave, so it never just blinks
    const MIN_SHOWN_MS = 800;

    let visible = $state(false);

    $effect(() => {
        if (!navigating.to) return;
        let shownAt = 0;
        const show = setTimeout(() => {
            visible = true;
            shownAt = performance.now();
        }, DELAY_MS);
        return () => {
            clearTimeout(show);
            if (!shownAt) return;
            setTimeout(() => (visible = false), Math.max(0, MIN_SHOWN_MS - (performance.now() - shownAt)));
        };
    });
</script>

{#if visible}
    <div
        role="status"
        aria-label="Loading"
        class="fixed inset-0 z-50 flex items-center justify-center bg-mist-950"
        in:fade={{ duration: 200 }}
        out:fade={{ duration: 300 }}
    >
        <Logo animated class="size-24" />
    </div>
{/if}
