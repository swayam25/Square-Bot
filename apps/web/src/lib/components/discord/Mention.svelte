<script lang="ts">
    import GuildIcon from "#lib/components/ui/GuildIcon.svelte";
    import MaterialSymbolsChevronRightRounded from "~icons/material-symbols/chevron-right-rounded";
    import MaterialSymbolsPlayShapesRounded from "~icons/material-symbols/play-shapes-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import MaterialSymbolsVolumeUpRounded from "~icons/material-symbols/volume-up-rounded";

    let {
        kind = "channel",
        name,
        color,
        guild,
    }: {
        kind?: "channel" | "voice" | "user" | "role" | "command";
        name: string;
        color?: string | null;
        guild?: { name: string; iconUrl: string | null };
    } = $props();

    const role = $derived(kind === "role" && color);
</script>

<span
    style:--role={role ? color : undefined}
    class={[
        "cursor-pointer rounded-[3px] px-0.5 font-medium whitespace-nowrap transition-colors",
        role
            ? "bg-[color-mix(in_srgb,var(--role)_10%,transparent)] text-(--role) hover:bg-[color-mix(in_srgb,var(--role)_30%,transparent)]"
            : "bg-dc-blurple/30 text-dc-mention hover:bg-dc-blurple hover:text-white",
    ]}
>
    {#if guild}
        <GuildIcon
            src={guild.iconUrl}
            name={guild.name}
            class="mr-1 inline-block size-[1.1em] rounded-full align-[-0.2em]"
        />{guild.name}<MaterialSymbolsChevronRightRounded aria-hidden="true" class="mx-0.5 inline size-[1em] align-[-0.125em] opacity-70" />
    {/if}
    {#if kind === "channel"}
        <MaterialSymbolsTagRounded aria-hidden="true" class="mr-0.5 inline size-[1em] align-[-0.125em]" />
    {:else if kind === "voice"}
        <MaterialSymbolsVolumeUpRounded aria-hidden="true" class="mr-0.5 inline size-[1em] align-[-0.125em]" />
    {:else if kind === "command"}
        <MaterialSymbolsPlayShapesRounded aria-hidden="true" class="mr-0.5 inline size-[1em] align-[-0.125em]" />
    {/if}{kind === "user" || kind === "role" ? "@" : ""}{name}
</span>
