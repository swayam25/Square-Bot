import { untrack } from "svelte";

export type Tone = "success" | "info" | "warning" | "error" | "loading";
export type ToastPerson = { name: string; avatarUrl: string | null };
export type Toast = { id: string; tone: Tone; message: string; description?: string; person?: ToastPerson; createdAt: number };
type Options = { id?: string; description?: string; person?: ToastPerson; duration?: number };

const DURATION: Record<Tone, number | undefined> = { success: 3200, info: 3200, warning: 6000, error: 6000, loading: undefined };

let nextId = 0;

class Toasts {
    #items = $state<Toast[]>([]);
    #timers = new Map<string, ReturnType<typeof setTimeout>>();

    current = $derived(
        this.#items.reduce<Toast | null>((best, item) => {
            if (!best) return item;
            if ((item.tone === "loading") !== (best.tone === "loading")) return item.tone === "loading" ? best : item;
            return item.createdAt >= best.createdAt ? item : best;
        }, null),
    );

    // Untracked, so an $effect can show a toast without subscribing to the list it changes
    show(tone: Tone, message: string, { id = `toast-${++nextId}`, description, person, duration = DURATION[tone] }: Options = {}) {
        untrack(() => {
            const replaced = tone === "loading" ? [] : this.#items.filter((item) => item.tone !== "loading").map((item) => item.id);
            for (const old of [...replaced, id]) this.#clear(old);
            this.#items = [
                ...this.#items.filter((item) => item.id !== id && !replaced.includes(item.id)),
                { id, tone, message, description, person, createdAt: performance.now() },
            ];
            if (duration)
                this.#timers.set(
                    id,
                    setTimeout(() => this.dismiss(id), duration),
                );
        });
        return id;
    }

    dismiss(id: string) {
        this.#clear(id);
        untrack(() => (this.#items = this.#items.filter((item) => item.id !== id)));
    }

    #clear(id: string) {
        clearTimeout(this.#timers.get(id));
        this.#timers.delete(id);
    }
}

export const toasts = new Toasts();

export const toast = {
    success: (message: string, options?: Options) => toasts.show("success", message, options),
    info: (message: string, options?: Options) => toasts.show("info", message, options),
    warning: (message: string, options?: Options) => toasts.show("warning", message, options),
    error: (message: string, options?: Options) => toasts.show("error", message, options),
    loading: (message: string, options?: Options) => toasts.show("loading", message, options),
    dismiss: (id: string) => toasts.dismiss(id),
};
