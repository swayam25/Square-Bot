<script lang="ts">
    import DiscordAccessories from "#lib/components/discord/DiscordAccessories.svelte";
    import DiscordComponents from "#lib/components/discord/DiscordComponents.svelte";
    import DiscordDivider from "#lib/components/discord/DiscordDivider.svelte";
    import DiscordEmbed from "#lib/components/discord/DiscordEmbed.svelte";
    import DiscordFile from "#lib/components/discord/DiscordFile.svelte";
    import DiscordGallery from "#lib/components/discord/DiscordGallery.svelte";
    import DiscordImageViewer from "#lib/components/discord/DiscordImageViewer.svelte";
    import DiscordMarkdown from "#lib/components/discord/DiscordMarkdown.svelte";
    import DiscordMessage from "#lib/components/discord/DiscordMessage.svelte";
    import DiscordReactions from "#lib/components/discord/DiscordReactions.svelte";
    import DiscordSystemMessage from "#lib/components/discord/DiscordSystemMessage.svelte";
    import DiscordWindow from "#lib/components/discord/DiscordWindow.svelte";
    import HashIcon from "#lib/components/discord/HashIcon.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { setDiscord } from "#lib/discord/context.ts";
    import { calendar, clock, fullTime, longDate, sameDay } from "#lib/discord/markdown.ts";
    import type { Transcript, TranscriptFile, TranscriptMessage } from "@square/api-client";
    import type { Snippet } from "svelte";

    let {
        transcript,
        topic,
        fileUrl,
        aside,
        footer,
    }: {
        transcript: Transcript;
        topic?: string;
        fileUrl: (file: TranscriptFile) => string | null;
        aside?: Snippet;
        footer?: Snippet;
    } = $props();

    const GROUP_WINDOW = 7 * 60_000;
    // Long channels skip drawing what's off screen. Short ones don't need it, and jumps land more exactly without it
    const LAZY_FROM = 300;

    let viewing = $state<string | null>(null);
    setDiscord({
        get users() {
            return transcript.users ?? {};
        },
        get roles() {
            return transcript.roles ?? {};
        },
        get channels() {
            return transcript.channels ?? {};
        },
        fileUrl: (file) => fileUrl(file),
        view: (src) => (viewing = new URL(src, location.href).href),
    });

    const rows = $derived.by(() => {
        const rows: { message: TranscriptMessage; day: boolean; first: boolean }[] = [];
        let previous: TranscriptMessage | null = null;
        for (const message of transcript.messages) {
            const day = !previous || !sameDay(previous.time, message.time);
            const joined =
                previous !== null &&
                !day &&
                previous.author === message.author &&
                message.time - previous.time < GROUP_WINDOW &&
                !(message.system || previous.system || message.reply || message.replyDeleted || message.command);
            rows.push({ message, day, first: !joined });
            previous = message;
        }
        return rows;
    });
    const lazy = $derived(transcript.messages.length > LAZY_FROM && "[contain-intrinsic-size:auto_3rem] [content-visibility:auto]");

    let flashed = $state<string | null>(null);
    function jump(id: string) {
        const target = document.getElementById(`m${id}`);
        if (!target) return;
        target.scrollIntoView({ block: "center", behavior: "smooth" });
        flashed = null;
        requestAnimationFrame(() => (flashed = id));
    }

    function replyOf(message: TranscriptMessage) {
        if (!message.reply) return message.replyDeleted ? ("deleted" as const) : undefined;
        const { id, author, preview, attachment, ping } = message.reply;
        const user = transcript.users?.[author];
        return {
            name: user?.name ?? "Unknown User",
            avatar: user?.avatar ?? null,
            color: user?.color,
            bot: user?.bot,
            ping,
            text: preview,
            attachment,
            onclick: () => jump(id),
        };
    }

    function commandOf(message: TranscriptMessage) {
        if (!message.command) return {};
        const user = transcript.users?.[message.command.user];
        return { command: message.command.name, commandUser: { name: user?.name ?? "Unknown User", avatar: user?.avatar ?? null } };
    }
</script>

<DiscordWindow channel={transcript.channel} {topic} spaced={false} {aside} {footer} class="shadow-none">
    <div class="mx-4 mb-2">
        <div class="mb-2 flex size-17 items-center justify-center rounded-full bg-dc-surface text-dc-strong">
            <HashIcon class="size-10.5" />
        </div>
        <h2 class="my-2 text-3xl leading-10 font-bold wrap-anywhere text-dc-strong">Welcome to #{transcript.channel}!</h2>
        <p class="text-dc-muted">This is the start of the #{transcript.channel} channel.</p>
    </div>

    {#each rows as { message, day, first } (message.id)}
        {@const author = transcript.users?.[message.author]}
        {@const media = (message.attachments ?? []).filter((file) => file.kind === "image" || file.kind === "video")}
        {@const files = (message.attachments ?? []).filter((file) => file.kind !== "image" && file.kind !== "video")}
        {#if day}<DiscordDivider label={longDate(message.time)} />{/if}
        {#if message.system}
            <DiscordSystemMessage
                id="m{message.id}"
                kind={message.system}
                time={calendar(message.time)}
                timeTitle={fullTime(message.time)}
                class={[!day && "mt-4.25", lazy]}
            >
                {message.content}
            </DiscordSystemMessage>
        {:else}
            <DiscordMessage
                id="m{message.id}"
                name={author?.name ?? "Unknown User"}
                avatar={author?.avatar ?? null}
                color={author?.color}
                bot={author?.bot ?? false}
                time={first ? calendar(message.time) : clock(message.time)}
                timeTitle={fullTime(message.time)}
                compact={!first}
                reply={first ? replyOf(message) : undefined}
                {...first ? commandOf(message) : {}}
                class={[first && !day && "mt-4.25", flashed === message.id && "animate-dc-flash", lazy]}
            >
                {#if message.content}<DiscordMarkdown text={message.content} edited={message.edited} />{/if}
                {#if media.length || files.length || message.embeds?.length || message.components?.length || message.stickers?.length || message.reactions?.length}
                    <DiscordAccessories>
                        {#if media.length}<DiscordGallery files={media} />{/if}
                        {#each files as file, index (index)}<DiscordFile {file} />{/each}
                        {#each message.embeds ?? [] as embed, index (index)}<DiscordEmbed {embed} />{/each}
                        {#if message.components?.length}<DiscordComponents components={message.components} />{/if}
                        {#each message.stickers ?? [] as sticker, index (index)}
                            <Tooltip lazy content={sticker.name}
                                ><img src={sticker.url} alt={sticker.name} loading="lazy" class="size-40 object-contain" /></Tooltip
                            >
                        {/each}
                        {#if message.reactions?.length}<DiscordReactions reactions={message.reactions} />{/if}
                    </DiscordAccessories>
                {/if}
            </DiscordMessage>
        {/if}
    {/each}
</DiscordWindow>

<DiscordImageViewer bind:src={viewing} />
