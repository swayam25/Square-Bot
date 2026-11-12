<script lang="ts">
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
        <svg viewBox="0 0 24 24" aria-hidden="true" class="mr-0.5 inline size-[1em] fill-current align-[-0.125em]">
            <path
                fill-rule="evenodd"
                d="M10.99 3.16A1 1 0 1 0 9 2.84L8.15 8H4a1 1 0 0 0 0 2h3.82l-.67 4H3a1 1 0 1 0 0 2h3.82l-.8 4.84a1 1 0 0 0 1.97.32L8.85 16h4.97l-.8 4.84a1 1 0 0 0 1.97.32l.86-5.16H20a1 1 0 1 0 0-2h-3.82l.67-4H21a1 1 0 1 0 0-2h-3.82l.8-4.84a1 1 0 1 0-1.97-.32L15.15 8h-4.97l.8-4.84ZM14.15 14l.67-4H9.85l-.67 4h4.97Z"
            />
        </svg>
    {:else if kind === "voice"}
        <MaterialSymbolsVolumeUpRounded aria-hidden="true" class="mr-0.5 inline size-[1em] align-[-0.125em]" />
    {:else if kind === "command"}
        <MaterialSymbolsPlayShapesRounded aria-hidden="true" class="mr-0.5 inline size-[1em] align-[-0.125em]" />
    {/if}{kind === "user" || kind === "role" ? "@" : kind === "command" ? "/" : ""}{name}
</span>
