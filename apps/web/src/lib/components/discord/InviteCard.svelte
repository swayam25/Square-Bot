<script module lang="ts">
    export type Invites = {
        name: string;
        username: string;
        avatar: string | null;
        guildName: string;
        guildIcon: string | null;
        rank: number | null;
        regular: number;
        left: number;
        fake: number;
        bonus: number;
        fakeDays: number;
    };
</script>

<script lang="ts">
    import CardFrame from "#lib/components/discord/CardFrame.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Chip from "#lib/components/ui/Chip.svelte";
    import SplitBar from "#lib/components/ui/SplitBar.svelte";
    import { formatCount } from "#lib/format.ts";

    let { data }: { data: Invites } = $props();

    const kinds = $derived([
        { label: "Regular", value: data.regular, class: "bg-accent" },
        { label: "Bonus", value: data.bonus, class: "bg-emerald-400" },
        { label: "Left", value: data.left, class: "bg-amber-400" },
        { label: "Fake", value: data.fake, class: "bg-red-400" },
    ]);
    const counted = $derived(kinds.map((kind) => ({ ...kind, value: Math.max(kind.value, 0) })));
    const share = $derived.by(() => {
        const sum = counted.reduce((total, kind) => total + kind.value, 0);
        return sum ? Math.round((100 * counted[0].value) / sum) : 0;
    });
</script>

<CardFrame>
    <div class="flex items-center gap-4">
        <Avatar src={data.avatar} name={data.name} class="size-14 text-2xl" />
        <div class="flex min-w-0 flex-1 flex-col gap-0.5">
            <span class="truncate font-display text-xl font-semibold">{data.name}</span>
            <div class="flex items-center gap-2 text-sm text-gray-400">
                <span class="font-mono">@{data.username}</span>
                <span>·</span>
                {#if data.guildIcon}
                    <img src={data.guildIcon} alt="" class="size-4 rounded-md" />
                {/if}
                <span class="truncate">{data.guildName}</span>
            </div>
        </div>
        <Chip tone={data.rank ? "accent" : "muted"} class="font-mono text-sm">{data.rank ? `Rank #${data.rank}` : "Unranked"}</Chip>
    </div>

    <div class="flex flex-col gap-4">
        <div class="flex items-baseline gap-4">
            <span class="font-mono text-5xl font-medium tracking-tight">{formatCount(data.regular + data.bonus)}</span>
            <span class="text-gray-400">total invites</span>
        </div>
        <SplitBar parts={counted} label={counted[0].value ? `${share}% regular` : undefined} />
    </div>

    <div class="flex gap-2">
        {#each kinds as kind (kind.label)}
            <div class="flex flex-1 flex-col gap-2 rounded-2xl bg-gray-900 p-4">
                <span class="flex items-center gap-2 text-sm text-gray-400"
                    ><span class={["size-2 rounded-full", kind.class]}></span>{kind.label}</span
                >
                <span class="font-mono text-2xl font-medium">{formatCount(kind.value)}</span>
            </div>
        {/each}
    </div>

    <p class="text-xs text-gray-400">
        Total counts regular and bonus invites. Fake invites are accounts younger than {data.fakeDays} days when they joined.
    </p>
</CardFrame>
