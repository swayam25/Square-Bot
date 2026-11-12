<script module lang="ts">
    // Called straight from the click: browsers only grant full screen inside the user's own gesture
    export function enterFullscreen() {
        document.documentElement.requestFullscreen?.({ navigationUI: "hide" }).catch(() => {});
    }
</script>

<script lang="ts">
    import Cover from "#lib/components/ui/Cover.svelte";
    import Portal from "#lib/components/ui/Portal.svelte";
    import { Dialog } from "@ark-ui/svelte/dialog";
    import type { Track } from "@square/api-client";
    import MaterialSymbolsCloseFullscreenRounded from "~icons/material-symbols/close-fullscreen-rounded";
    import Lyrics from "./Lyrics.svelte";

    let {
        open = $bindable(false),
        guild,
        track,
        position,
        playing,
        lyricsOff,
    }: { open?: boolean; guild: string; track: Track; position: number; playing: boolean; lyricsOff: string | false } = $props();

    const IDLE_MS = 2500;
    let idle = $state(false);
    let timer: ReturnType<typeof setTimeout> | undefined;
    function wake() {
        idle = false;
        clearTimeout(timer);
        timer = setTimeout(() => (idle = true), IDLE_MS);
    }

    $effect(() => {
        if (!open) return;
        wake();
        // Leaving full screen from the browser (Esc, F11, the system bar) leaves the view too
        const onFullscreen = () => {
            if (!document.fullscreenElement) open = false;
        };
        // Keeps the screen awake for reading along; the browser drops the lock whenever the tab hides
        let lock: WakeLockSentinel | null = null;
        let closed = false;
        const keepAwake = async () => {
            if (document.visibilityState !== "visible" || !("wakeLock" in navigator)) return;
            try {
                const next = await navigator.wakeLock.request("screen");
                if (closed) void next.release();
                else lock = next;
            } catch {
                // Denied, as with a low battery: the screen just sleeps as usual
            }
        };
        void keepAwake();
        document.addEventListener("fullscreenchange", onFullscreen);
        document.addEventListener("visibilitychange", keepAwake);
        return () => {
            closed = true;
            clearTimeout(timer);
            document.removeEventListener("fullscreenchange", onFullscreen);
            document.removeEventListener("visibilitychange", keepAwake);
            void lock?.release().catch(() => {});
            if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
        };
    });
</script>

<Dialog.Root bind:open lazyMount unmountOnExit>
    <Portal>
        <Dialog.Positioner class="fixed inset-0 z-50">
            <Dialog.Content
                class={[
                    "relative isolate flex size-full flex-col overflow-hidden bg-mist-950 outline-none data-[state=closed]:animate-fade-out data-[state=open]:animate-shell-in",
                    idle && "cursor-none",
                ]}
                onpointermove={wake}
                onpointerdown={wake}
                onkeydown={wake}
            >
                {#if track.artworkUrl}
                    <img
                        src={track.artworkUrl}
                        alt=""
                        aria-hidden="true"
                        referrerpolicy="no-referrer"
                        class="absolute inset-0 -z-10 size-full scale-150 object-cover opacity-40 blur-3xl saturate-150"
                    />
                {/if}
                <span aria-hidden="true" class="absolute inset-0 -z-10 bg-linear-to-b from-mist-950/20 to-mist-950/70"></span>
                <Dialog.Title class="sr-only">{track.title} by {track.author}</Dialog.Title>

                <Dialog.CloseTrigger
                    aria-label="Exit full screen"
                    class={[
                        "absolute top-[max(1rem,env(safe-area-inset-top))] right-4 z-10 flex size-12 items-center justify-center rounded-full bg-black/30 text-mist-100 backdrop-blur-xl transition-opacity duration-500 hover:bg-black/50 focus-visible:opacity-100 md:top-6 md:right-6",
                        idle ? "pointer-events-none opacity-0" : "opacity-100",
                    ]}
                >
                    <MaterialSymbolsCloseFullscreenRounded class="size-6" />
                </Dialog.CloseTrigger>

                {#if lyricsOff}
                    <div class="flex flex-1 flex-col items-center justify-center gap-8 p-8 text-center">
                        <Cover src={track.artworkUrl} class="size-[min(80vw,60dvh)] rounded-4xl text-accent shadow-2xl shadow-black/50" />
                        {@render info("items-center")}
                    </div>
                {:else}
                    <div
                        class="mx-auto grid min-h-0 w-full max-w-7xl flex-1 grid-rows-[auto_minmax(0,1fr)] gap-4 pt-[max(1rem,env(safe-area-inset-top))] lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] lg:grid-rows-1 lg:gap-16 lg:p-16"
                    >
                        <div class="flex min-w-0 items-center gap-4 pr-20 pl-4 lg:flex-col lg:items-start lg:justify-center lg:gap-8 lg:p-0">
                            <Cover
                                src={track.artworkUrl}
                                class="size-16 rounded-2xl text-accent shadow-xl shadow-black/50 lg:aspect-square lg:h-auto lg:w-[min(100%,60dvh)] lg:rounded-4xl lg:shadow-2xl"
                            />
                            {@render info("items-start")}
                        </div>
                        <div class="flex min-h-0 flex-col pb-[env(safe-area-inset-bottom)]">
                            {#key track.identifier}
                                <Lyrics {guild} {track} {position} {playing} zen />
                            {/key}
                        </div>
                    </div>
                {/if}
            </Dialog.Content>
        </Dialog.Positioner>
    </Portal>
</Dialog.Root>

{#snippet info(align: string)}
    <div class={["flex min-w-0 flex-col gap-1 lg:gap-2", align]}>
        <p class="line-clamp-2 font-display text-lg font-semibold lg:text-4xl">{track.title}</p>
        <p class="truncate text-sm text-mist-400 lg:text-xl">{track.author}</p>
    </div>
{/snippet}
