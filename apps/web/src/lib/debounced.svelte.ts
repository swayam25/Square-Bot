// Follows `read` once it holds still for `ms`. An empty value lands at once, so clearing a search box is instant.
// Create it while a component is starting up, since it runs an effect
export class Debounced<T> {
    current = $state() as T;

    constructor(read: () => T, ms: number) {
        this.current = read();
        $effect(() => {
            const next = read();
            if (!next) {
                this.current = next;
                return;
            }
            const timer = setTimeout(() => (this.current = next), ms);
            return () => clearTimeout(timer);
        });
    }
}
