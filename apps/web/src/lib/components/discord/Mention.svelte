<script lang="ts">
    import HashIcon from "#lib/components/discord/HashIcon.svelte";
    import MaterialSymbolsPlayShapesRounded from "~icons/material-symbols/play-shapes-rounded";
    import MaterialSymbolsVolumeUpRounded from "~icons/material-symbols/volume-up-rounded";

    let {
        kind = "channel",
        name,
        color,
    }: {
        kind?: "channel" | "voice" | "user" | "role" | "command";
        name: string;
        color?: string | null;
    } = $props();

    const role = $derived(kind === "role" && color);
</script>

<span
    style:--role={role ? color : undefined}
    class={[
        "rounded-[3px] px-0.5 font-medium whitespace-nowrap",
        role ? "bg-[color-mix(in_srgb,var(--role)_10%,transparent)] text-(--role)" : "bg-[#5865f2]/30 text-[#c9cdfb]",
    ]}
>
    {#if kind === "channel"}
        <HashIcon class="mr-0.5 inline size-[1em] align-[-0.125em]" />
    {:else if kind === "voice"}
        <MaterialSymbolsVolumeUpRounded aria-hidden="true" class="mr-0.5 inline size-[1em] align-[-0.125em]" />
    {:else if kind === "command"}
        <MaterialSymbolsPlayShapesRounded aria-hidden="true" class="mr-0.5 inline size-[1em] align-[-0.125em]" />
    {/if}{kind === "user" || kind === "role" ? "@" : kind === "command" ? "/" : ""}{name}
</span>
