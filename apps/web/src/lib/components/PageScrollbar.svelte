<script lang="ts">
    import { onMount } from "svelte";

    const MIN_THUMB = 40;
    const IDLE_MS = 900;
    const REPEAT_DELAY_MS = 300;
    const REPEAT_EVERY_MS = 50;

    let enabled = $state(false);
    let scrollable = $state(false);
    let thumb = $state({ top: 0, height: 0 });
    let active = $state(false);
    let hovering = $state(false);
    let dragging = $state(false);
    const visible = $derived(scrollable && (active || hovering || dragging));

    let frame = 0;
    let idle: ReturnType<typeof setTimeout> | undefined;

    function measure() {
        frame = 0;
        const { scrollHeight, clientHeight } = document.documentElement;
        scrollable = scrollHeight > clientHeight + 1;
        if (!scrollable) return;
        const height = Math.max(MIN_THUMB, (clientHeight / scrollHeight) * clientHeight);
        thumb = { height, top: (scrollY / (scrollHeight - clientHeight)) * (clientHeight - height) };
    }

    const schedule = () => (frame ||= requestAnimationFrame(measure));

    onMount(() => {
        if (!matchMedia("(pointer: fine)").matches) return;
        enabled = true;
        measure();
        const onScroll = () => {
            schedule();
            active = true;
            clearTimeout(idle);
            idle = setTimeout(() => (active = false), IDLE_MS);
        };
        addEventListener("scroll", onScroll, { passive: true });
        addEventListener("resize", schedule);
        const observer = new ResizeObserver(schedule);
        observer.observe(document.body);
        return () => {
            removeEventListener("scroll", onScroll);
            removeEventListener("resize", schedule);
            observer.disconnect();
            clearTimeout(idle);
            cancelAnimationFrame(frame);
        };
    });

    function press(event: PointerEvent) {
        if (event.button !== 0) return;
        event.preventDefault();
        const strip = event.currentTarget as HTMLElement;
        strip.setPointerCapture(event.pointerId);
        let pointerY = event.clientY;
        let move: (e: PointerEvent) => void;
        let stop = () => {};

        if (pointerY >= thumb.top && pointerY <= thumb.top + thumb.height) {
            dragging = true;
            const { scrollHeight, clientHeight } = document.documentElement;
            const ratio = (scrollHeight - clientHeight) / (clientHeight - thumb.height);
            const start = { y: pointerY, scroll: scrollY };
            move = (e) => scrollTo({ top: start.scroll + (e.clientY - start.y) * ratio, behavior: "instant" });
        } else {
            const page = () => {
                const direction = pointerY < thumb.top ? -1 : pointerY > thumb.top + thumb.height ? 1 : 0;
                if (!direction) return clearInterval(repeat);
                scrollBy({ top: direction * document.documentElement.clientHeight * 0.875, behavior: "instant" });
                measure();
            };
            let repeat: ReturnType<typeof setInterval> | undefined;
            page();
            const delay = setTimeout(() => (repeat = setInterval(page, REPEAT_EVERY_MS)), REPEAT_DELAY_MS);
            move = (e) => (pointerY = e.clientY);
            stop = () => {
                clearTimeout(delay);
                clearInterval(repeat);
            };
        }

        const end = () => {
            dragging = false;
            stop();
            strip.removeEventListener("pointermove", move);
            strip.removeEventListener("pointerup", end);
            strip.removeEventListener("pointercancel", end);
        };
        strip.addEventListener("pointermove", move);
        strip.addEventListener("pointerup", end);
        strip.addEventListener("pointercancel", end);
    }
</script>

<svelte:head>
    <!-- Without JavaScript this bar never draws, so keep the native one -->
    <noscript
        ><style>
            html {
                scrollbar-width: auto;
            }
        </style></noscript
    >
</svelte:head>

{#if enabled && scrollable}
    <div
        aria-hidden="true"
        class="fixed inset-y-0 right-0 z-45 w-3"
        onpointerenter={() => (hovering = true)}
        onpointerleave={() => (hovering = false)}
        onpointerdown={press}
    >
        <div
            class={[
                "pointer-events-none absolute right-0.5 rounded-full transition-[opacity,width,background-color] duration-300",
                dragging ? "w-2.5 bg-mist-300/70" : hovering ? "w-2.5 bg-mist-400/60" : "w-1.5 bg-mist-400/40",
                !visible && "opacity-0",
            ]}
            style="top: {thumb.top}px; height: {thumb.height}px"
        ></div>
    </div>
{/if}
