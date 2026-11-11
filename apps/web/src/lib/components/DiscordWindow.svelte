<script lang="ts">
    import type { Snippet } from "svelte";

    let { channel, children }: { channel: string; children: Snippet } = $props();
</script>

<div class="w-full overflow-hidden rounded-2xl bg-[#1a1a1e] text-base leading-5.5 text-[#dfe0e2] shadow-2xl shadow-black/40">
    <div class="flex h-12 items-center gap-2 border-b border-[#29292d] px-4">
        <svg viewBox="0 0 24 24" aria-hidden="true" class="size-6 fill-[#81828a]">
            <path
                fill-rule="evenodd"
                d="M10.99 3.16A1 1 0 1 0 9 2.84L8.15 8H4a1 1 0 0 0 0 2h3.82l-.67 4H3a1 1 0 1 0 0 2h3.82l-.8 4.84a1 1 0 0 0 1.97.32L8.85 16h4.97l-.8 4.84a1 1 0 0 0 1.97.32l.86-5.16H20a1 1 0 1 0 0-2h-3.82l.67-4H21a1 1 0 1 0 0-2h-3.82l.8-4.84a1 1 0 1 0-1.97-.32L15.15 8h-4.97l.8-4.84ZM14.15 14l.67-4H9.85l-.67 4h4.97Z"
            />
        </svg>
        <span class="font-semibold text-[#fbfbfb]">{channel}</span>
    </div>
    <div class="flex flex-col gap-4.25 pt-4 pb-6">{@render children()}</div>
</div>
