<script lang="ts">
    let {
        viewport,
        inset = 4,
    }: {
        viewport: HTMLElement | null | undefined;
        inset?: number;
    } = $props();

    const MIN_THUMB = 32;
    const IDLE_MS = 900;
    const EDGE_PX = 12;

    let enabled = $state(false);
    let frame = $state({ top: 0, left: 0, width: 0, height: 0 });
    let bar = $state({ scrollable: false, start: 0, size: 0 });
    let active = $state(false);
    let nearEdge = $state(false);
    let overThumb = $state(false);
    let dragging = $state(false);
    const visible = $derived(bar.scrollable && (active || nearEdge || overThumb || dragging));

    const trackLength = () => frame.height - inset * 2;

    function update(el: HTMLElement) {
        frame = { top: el.offsetTop + el.clientTop, left: el.offsetLeft + el.clientLeft, width: el.clientWidth, height: el.clientHeight };
        const { clientHeight, scrollHeight, scrollTop } = el;
        if (scrollHeight <= clientHeight + 1) {
            bar = { scrollable: false, start: 0, size: 0 };
            return;
        }
        const track = trackLength();
        const size = Math.max(MIN_THUMB, (clientHeight / scrollHeight) * track);
        bar = { scrollable: true, size, start: (scrollTop / (scrollHeight - clientHeight)) * (track - size) };
    }

    $effect(() => {
        const el = viewport;
        if (!el || !matchMedia("(pointer: fine)").matches) return;
        enabled = true;
        el.dataset.overlayScrollbar = "";

        // Every measurement waits for a frame, so nothing here reads state while the effect runs
        let raf = 0;
        const schedule = () => (raf ||= requestAnimationFrame(() => ((raf = 0), update(el))));
        let idle: ReturnType<typeof setTimeout> | undefined;

        const onScroll = () => {
            schedule();
            active = true;
            clearTimeout(idle);
            idle = setTimeout(() => (active = false), IDLE_MS);
        };
        const onPointerMove = (event: PointerEvent) => {
            if (event.pointerType !== "mouse") return;
            const near = el.getBoundingClientRect().right - event.clientX <= EDGE_PX;
            if (near === nearEdge) return;
            nearEdge = near;
            if (near) schedule();
        };
        const onPointerLeave = () => (nearEdge = false);

        schedule();
        el.addEventListener("scroll", onScroll, { passive: true });
        el.addEventListener("pointermove", onPointerMove, { passive: true });
        el.addEventListener("pointerleave", onPointerLeave);
        const observer = new ResizeObserver(schedule);
        observer.observe(el);

        return () => {
            delete el.dataset.overlayScrollbar;
            el.removeEventListener("scroll", onScroll);
            el.removeEventListener("pointermove", onPointerMove);
            el.removeEventListener("pointerleave", onPointerLeave);
            observer.disconnect();
            clearTimeout(idle);
            cancelAnimationFrame(raf);
            enabled = false;
        };
    });

    function startDrag(event: PointerEvent) {
        const el = viewport;
        if (!el || event.button !== 0) return;
        event.preventDefault();
        const thumb = event.currentTarget as HTMLElement;
        thumb.setPointerCapture(event.pointerId);
        dragging = true;
        const start = { y: event.clientY, scroll: el.scrollTop };
        const ratio = (el.scrollHeight - el.clientHeight) / (trackLength() - bar.size);
        const move = (e: PointerEvent) => el.scrollTo({ top: start.scroll + (e.clientY - start.y) * ratio, behavior: "instant" });
        const end = () => {
            dragging = false;
            thumb.removeEventListener("pointermove", move);
            thumb.removeEventListener("pointerup", end);
            thumb.removeEventListener("pointercancel", end);
        };
        thumb.addEventListener("pointermove", move);
        thumb.addEventListener("pointerup", end);
        thumb.addEventListener("pointercancel", end);
    }
</script>

{#if enabled && bar.scrollable}
    <div
        aria-hidden="true"
        class="pointer-events-none absolute z-10"
        style="top: {frame.top}px; left: {frame.left}px; width: {frame.width}px; height: {frame.height}px"
    >
        <div
            role="presentation"
            class={[
                "pointer-events-auto absolute right-0.5 cursor-grab rounded-full transition-[opacity,width,background-color] duration-300",
                dragging ? "w-2.5 cursor-grabbing bg-mist-300/70" : "w-1.5 bg-mist-400/40 hover:w-2.5 hover:bg-mist-400/60",
                !visible && "pointer-events-none opacity-0",
            ]}
            style="top: {inset + bar.start}px; height: {bar.size}px"
            onpointerenter={() => (overThumb = true)}
            onpointerleave={() => (overThumb = false)}
            onpointerdown={startDrag}
        ></div>
    </div>
{/if}
