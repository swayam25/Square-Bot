import { createContext, type Snippet } from "svelte";

export class Details {
    title = $state("");
    content = $state<Snippet | null>(null);
    key = $state<string | null>(null);

    show(title: string, content: Snippet, key?: string) {
        this.title = title;
        this.content = content;
        this.key = key ?? null;
    }

    close() {
        this.content = null;
        this.key = null;
    }
}

export const [getDetails, setDetails] = createContext<Details>();
