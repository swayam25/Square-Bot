<script lang="ts">
    import swayam from "#lib/assets/discord/swayam.webp";
    import square from "#lib/assets/square.svg";
    import DiscordMarkdown from "#lib/components/discord/DiscordMarkdown.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import type { Snippet } from "svelte";
    import type { ClassValue } from "svelte/elements";
    import MaterialSymbolsImageRounded from "~icons/material-symbols/image-rounded";
    import MaterialSymbolsPlayShapesRounded from "~icons/material-symbols/play-shapes-rounded";
    import MaterialSymbolsVisibilityRounded from "~icons/material-symbols/visibility-rounded";

    let {
        id,
        name = "Square",
        avatar,
        color,
        bot = true,
        time = "9:04 PM",
        timeTitle,
        compact = false,
        command,
        commandUser = { name: "Swayam", avatar: swayam },
        reply,
        ephemeral = false,
        class: className,
        children,
    }: {
        id?: string;
        name?: string;
        // Left out, the message is from Square itself
        avatar?: string | null;
        color?: string | null;
        bot?: boolean;
        time?: string;
        timeTitle?: string;
        compact?: boolean;
        command?: string;
        commandUser?: { name: string; avatar: string | null };
        // The message this one answers, or "deleted" when that message is gone. No `text` means it had only files or cards
        reply?:
            | {
                  name: string;
                  avatar?: string | null;
                  color?: string | null;
                  bot?: boolean;
                  ping?: boolean;
                  text?: string;
                  attachment?: boolean;
                  onclick?: () => void;
              }
            | "deleted";
        ephemeral?: boolean;
        class?: ClassValue;
        children: Snippet;
    } = $props();

    let hovered = $state(false);
</script>

{#snippet spine()}
    <span aria-hidden="true" class="absolute top-1.75 -left-9 h-3.5 w-8 rounded-tl-md border-t-2 border-l-2 border-[#4e4f58]"></span>
{/snippet}

<div
    {id}
    role="article"
    onpointerenter={() => (hovered = true)}
    onpointerleave={() => (hovered = false)}
    class={[
        "group/message relative min-h-5.5 py-0.5 pr-4 pl-18 wrap-anywhere hover:bg-dc-hover",
        ephemeral && "bg-dc-blurple/5 shadow-[inset_2px_0_var(--color-dc-blurple)]",
        className,
    ]}
>
    {#if compact}
        <Tooltip lazy content={timeTitle} class="absolute top-0.5 left-0 w-16 justify-end pr-2 opacity-0 group-hover/message:opacity-100">
            <time class="text-[11px] leading-5.5 text-dc-muted">{time}</time>
        </Tooltip>
    {:else}
        {#if command}
            <div class="relative mb-1 flex h-4.5 items-center gap-1 text-sm leading-4.5 whitespace-nowrap text-[#efeff1]">
                {@render spine()}
                <Avatar src={commandUser.avatar} name={commandUser.name} class="size-4 text-2xs" animate={hovered} />
                <span class="mr-1 font-medium text-[#ababaf]">{commandUser.name}</span>
                used
                <span class="flex items-center gap-1 rounded bg-dc-blurple/24 px-0.5 text-xs text-dc-link">
                    <MaterialSymbolsPlayShapesRounded class="size-3.5" />
                    {command}
                </span>
            </div>
        {:else if reply}
            <div class="relative mb-1 flex h-4.5 min-w-0 items-center gap-1 text-sm leading-4.5 whitespace-nowrap text-dc-muted">
                {@render spine()}
                {#if reply === "deleted"}
                    <span class="italic">Original message was deleted</span>
                {:else}
                    <Avatar src={reply.avatar} name={reply.name} class="size-4 text-2xs" animate={hovered} />
                    {#if reply.bot}
                        <span class="shrink-0 rounded bg-dc-blurple px-1 text-2xs leading-3.75 font-semibold text-white">APP</span>
                    {/if}
                    <span style:color={reply.color || undefined} class="shrink-0 font-medium text-dc-strong opacity-80"
                        >{reply.ping ? "@" : ""}{reply.name}</span
                    >
                    <button
                        type="button"
                        class="flex min-w-0 cursor-pointer items-center gap-1 text-[#b5b6bc] hover:text-dc-strong"
                        onclick={reply.onclick}
                    >
                        {#if reply.text}
                            <DiscordMarkdown text={reply.text} inline class="truncate" />
                        {:else}
                            <span class="truncate italic">Click to see {reply.attachment ? "attachment" : "message"}</span>
                            {#if reply.attachment}<MaterialSymbolsImageRounded class="size-4 shrink-0" />{/if}
                        {/if}
                    </button>
                {/if}
            </div>
        {/if}
        <div class="relative leading-5.5">
            {#if avatar === undefined}
                <span class="absolute top-0 -left-14 flex size-10 items-center justify-center rounded-full bg-gray-950">
                    <img src={square} alt="" class="size-7" />
                </span>
            {:else}
                <Avatar src={avatar} {name} class="absolute! top-0 -left-14 size-10" animate={hovered} />
            {/if}
            <span style:color={color || undefined} class="font-medium text-dc-strong">{name}</span>
            {#if bot}
                <span
                    class="relative -top-px ml-1 inline-block rounded bg-dc-blurple px-1 align-middle text-2xs leading-3.75 font-semibold text-white"
                    >APP</span
                >
            {/if}
            <Tooltip lazy content={timeTitle} class="ml-1"><time class="text-xs font-medium text-dc-muted">{time}</time></Tooltip>
        </div>
    {/if}
    {@render children()}
    {#if ephemeral}
        <div class="mt-1 flex items-center gap-1 text-xs text-dc-muted">
            <MaterialSymbolsVisibilityRounded class="size-4" />
            Only you can see this •<span class="text-dc-link">Dismiss message</span>
        </div>
    {/if}
</div>
