<script lang="ts">
    const MESSAGES = [
        { name: 24, lines: [72] },
        { name: 32, lines: [88, 56] },
        { name: 20, lines: [40] },
        { name: 28, lines: [80, 64, 32] },
        { name: 24, lines: [60] },
    ];
</script>

<div aria-label="Loading the ticket" aria-busy="true" class="flex flex-col gap-6">
    <div aria-hidden="true" class="grid grid-cols-2 gap-2 rounded-3xl bg-gray-900 p-2 md:grid-cols-3">
        {#each [0, 1, 2] as i (i)}
            <div class="flex min-h-12 items-center gap-4 rounded-2xl bg-gray-800 p-2">
                <span class="size-8 shrink-0 skeleton rounded-full"></span>
                <span class="flex flex-1 flex-col gap-1.5">
                    <span class="h-3 w-16 skeleton rounded-full"></span>
                    <span class="h-3.5 w-24 skeleton rounded-full"></span>
                </span>
            </div>
        {/each}
        {#each [0, 1, 2] as i (i)}
            <div class="flex min-h-12 flex-col justify-center gap-1.5 rounded-2xl bg-gray-800 px-4 py-2">
                <span class="h-3 w-14 skeleton rounded-full"></span>
                <span class="h-3.5 w-32 max-w-full skeleton rounded-full"></span>
            </div>
        {/each}
    </div>

    <div aria-hidden="true" class="w-full overflow-hidden rounded-2xl bg-dc-bg">
        <div class="flex h-12 items-center gap-2 border-b border-dc-line px-4">
            <span class="size-5 skeleton rounded-md"></span>
            <span class="h-4 w-28 skeleton rounded-full"></span>
        </div>
        <div class="flex flex-col pt-4 pb-6">
            <div class="mx-4 mb-6 flex flex-col gap-3">
                <span class="size-17 skeleton rounded-full"></span>
                <span class="h-7 w-72 max-w-full skeleton rounded-full"></span>
                <span class="h-4 w-56 max-w-full skeleton rounded-full"></span>
            </div>
            <div class="flex flex-col gap-4.25">
                {#each MESSAGES as message, i (i)}
                    <div class="relative py-0.5 pr-4 pl-18">
                        <span class="absolute top-0.5 left-4 size-10 skeleton rounded-full" style:animation-delay="{i * 80}ms"></span>
                        <div class="flex h-5.5 items-center gap-2">
                            <span class="h-4 skeleton rounded-full" style:width="{message.name}%" style:animation-delay="{i * 80}ms"></span>
                            <span class="h-3 w-12 skeleton rounded-full" style:animation-delay="{i * 80}ms"></span>
                        </div>
                        {#each message.lines as width, line (line)}
                            <div class="flex h-5.5 items-center">
                                <span class="h-3.5 skeleton rounded-full" style:width="{width}%" style:animation-delay="{i * 80}ms"></span>
                            </div>
                        {/each}
                    </div>
                {/each}
            </div>
        </div>
    </div>
</div>
