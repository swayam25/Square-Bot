<script lang="ts">
    import DiscordEmoji from "#lib/components/discord/DiscordEmoji.svelte";
    import DiscordSpoiler from "#lib/components/discord/DiscordSpoiler.svelte";
    import Mention from "#lib/components/discord/Mention.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { getDiscord } from "#lib/discord/context.ts";
    import { fullTime, inline as inlineNodes, jumbo, parse, timestamp, type Inline } from "#lib/discord/markdown.ts";
    import type { ClassValue } from "svelte/elements";

    let {
        text,
        edited = false,
        inline = false,
        class: className,
    }: {
        text: string;
        edited?: boolean;
        inline?: boolean;
        class?: ClassValue;
    } = $props();

    const discord = getDiscord();
    const blocks = $derived(inline ? [] : parse(text));
    const large = $derived(!inline && jumbo(blocks));
</script>

{#snippet nodes(children: Inline[])}
    {#each children as node, index (index)}
        {#if node.type === "text"}{node.text}{:else if node.type === "break"}<br />{:else if node.type === "bold"}<strong class="font-bold"
                >{@render nodes(node.children)}</strong
            >{:else if node.type === "italic"}<em>{@render nodes(node.children)}</em>{:else if node.type === "underline"}<u
                >{@render nodes(node.children)}</u
            >{:else if node.type === "strike"}<s>{@render nodes(node.children)}</s>{:else if node.type === "spoiler"}<DiscordSpoiler
                >{@render nodes(node.children)}</DiscordSpoiler
            >{:else if node.type === "code"}<code
                class="rounded-sm border border-dc-code-border bg-dc-code p-[0.2em] font-mono text-[85%] leading-4.5 whitespace-pre-wrap"
                >{node.text}</code
            >{:else if node.type === "link"}<a href={node.href} target="_blank" rel="noopener noreferrer" class="text-dc-link hover:underline"
                >{@render nodes(node.children)}</a
            >{:else if node.type === "emoji"}<DiscordEmoji
                name={node.name}
                id={node.id}
                animated={node.animated}
                class={["mr-[0.05em] ml-[0.1em]", large ? "size-12" : inline ? "size-[1.2em]" : "size-[1.375em]"]}
            />{:else if node.type === "user"}<Mention
                kind="user"
                name={discord.users[node.id]?.name ?? "unknown-user"}
            />{:else if node.type === "role"}<Mention
                kind="role"
                name={discord.roles[node.id]?.name ?? "unknown-role"}
                color={discord.roles[node.id]?.color || null}
            />{:else if node.type === "channel"}<Mention
                kind="channel"
                name={discord.channels[node.id] ?? "unknown-channel"}
            />{:else if node.type === "time"}<Tooltip lazy content={fullTime(node.at)}
                ><time datetime={new Date(node.at).toISOString()} class="rounded-[3px] bg-white/6 px-0.5">{timestamp(node.at, node.style)}</time
                ></Tooltip
            >{/if}
    {/each}
{/snippet}

{#snippet mark()}
    {#if edited}<span class="ml-1 text-2xs text-dc-muted">(edited)</span>{/if}
{/snippet}

{#if inline}
    <span class={["min-w-0", className]}>{@render nodes(inlineNodes(text))}</span>
{:else}
    <div class={["min-w-0 wrap-anywhere", className]}>
        {#each blocks as block, index (index)}
            {@const last = index === blocks.length - 1}
            {#if block.type === "paragraph"}
                <p class={[large && "text-5xl leading-tight"]}>
                    {@render nodes(block.children)}{#if last}{@render mark()}{/if}
                </p>
            {:else if block.type === "heading1"}
                <h4 class="my-2 text-2xl leading-snug font-bold text-dc-strong first:mt-0 last:mb-0">{@render nodes(block.children)}</h4>
            {:else if block.type === "heading2"}
                <h5 class="my-2 text-xl leading-snug font-bold text-dc-strong first:mt-0 last:mb-0">{@render nodes(block.children)}</h5>
            {:else if block.type === "heading3"}
                <h6 class="my-2 text-base leading-snug font-bold text-dc-strong first:mt-0 last:mb-0">{@render nodes(block.children)}</h6>
            {:else if block.type === "subtext"}
                <p class="text-[13px] leading-4.5 text-dc-muted">{@render nodes(block.children)}</p>
            {:else if block.type === "quote"}
                <blockquote class="rounded-sm border-l-4 border-dc-border-strong pr-2 pl-3">{@render nodes(block.children)}</blockquote>
            {:else if block.type === "item"}
                <p class="relative pl-5 before:absolute before:left-1.5 before:content-['•']">{@render nodes(block.children)}</p>
            {:else if block.type === "codeblock"}
                <pre
                    class="mt-1.5 max-w-[90%] rounded-sm border border-dc-code-border bg-dc-code p-2 font-mono text-sm leading-4.5 wrap-break-word whitespace-pre-wrap">{block.text}</pre>
            {:else}
                <div class="h-5.5"></div>
            {/if}
            {#if last && block.type !== "paragraph"}{@render mark()}{/if}
        {/each}
    </div>
{/if}
