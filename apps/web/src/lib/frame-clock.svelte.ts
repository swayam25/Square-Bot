export class FrameClock {
    current = $state(Date.now());

    constructor(running: () => boolean) {
        $effect(() => {
            if (!running()) return;
            const tick = () => {
                this.current = Date.now();
                frame = requestAnimationFrame(tick);
            };
            let frame = requestAnimationFrame(tick);
            return () => cancelAnimationFrame(frame);
        });
    }
}
