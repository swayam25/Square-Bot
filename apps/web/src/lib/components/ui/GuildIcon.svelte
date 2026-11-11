<script module lang="ts">
    function acronym(name: string) {
        return (
            name
                .replace(/'s /g, " ")
                .replace(/\w+/g, (word) => word[0])
                .replace(/\s/g, "") || "?"
        );
    }
</script>

<script lang="ts">
    import { Avatar } from "@ark-ui/svelte/avatar";
    import type { ClassValue } from "svelte/elements";

    let { src, name, class: className = "size-12 rounded-2xl" }: { src?: string | null; name: string; class?: ClassValue } = $props();

    let status = $state<"loading" | "loaded" | "error">("loading");
    $effect.pre(() => {
        void src;
        status = "loading";
    });

    const letters = $derived(acronym(name));
    const scale = $derived(letters.length <= 2 ? 38 : letters.length <= 4 ? 30 : 22);
</script>

<Avatar.Root onStatusChange={(details) => (status = details.status)} class={["@container relative inline-flex shrink-0 overflow-hidden", className]}>
    <Avatar.Fallback
        class={[
            "flex size-full items-center justify-center bg-surface-2 font-medium whitespace-nowrap",
            src && status === "loading" && "animate-pulse",
        ]}
        style="font-size: {scale}cqw"
    >
        {#if !src || status === "error"}{letters}{/if}
    </Avatar.Fallback>
    {#if src}
        <Avatar.Image {src} alt={name} class="size-full animate-fade-in object-cover" />
    {/if}
</Avatar.Root>
