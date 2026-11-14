<script lang="ts">
    import type { Component } from "svelte";

    let { icon: Icon, text }: { icon: Component; text: string } = $props();
</script>

<span class="flex h-12 min-w-0 flex-1 items-center gap-2 rounded-full bg-gray-800 px-4 text-sm font-medium md:h-10">
    <Icon class="size-4 shrink-0 text-gray-400" />
    <span class="truncate">{text}</span>
</span>
