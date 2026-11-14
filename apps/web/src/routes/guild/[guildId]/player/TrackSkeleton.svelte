<script lang="ts">
    let { label }: { label: string } = $props();
</script>

<ul aria-label={label} aria-busy="true" class="flex flex-col gap-1">
    {#each [64, 48, 72, 56, 40, 68, 52, 60] as width, i (i)}
        <li class="flex items-center gap-4 p-2">
            <span class="size-12 shrink-0 skeleton rounded-xl" style:animation-delay="{i * 80}ms"></span>
            <span class="flex flex-1 flex-col gap-2">
                <span class="h-4 skeleton rounded-full" style:width="{width}%" style:animation-delay="{i * 80}ms"></span>
                <span class="h-3 w-1/4 skeleton rounded-full" style:animation-delay="{i * 80}ms"></span>
            </span>
            <span class="h-3 w-8 skeleton rounded-full" style:animation-delay="{i * 80}ms"></span>
        </li>
    {/each}
</ul>
