import { createSubscriber } from "svelte/reactivity";

let at = Date.now();

const subscribe = createSubscriber((update) => {
    let timer: ReturnType<typeof setTimeout>;
    const tick = () => {
        at = Date.now();
        update();
        timer = setTimeout(tick, 60_000 - (at % 60_000));
    };
    tick();
    return () => clearTimeout(timer);
});

export const now = {
    get current() {
        subscribe();
        return at;
    },
};
