<script lang="ts">
    import DiscordAccessories from "#lib/components/discord/DiscordAccessories.svelte";
    import DiscordActionRow from "#lib/components/discord/DiscordActionRow.svelte";
    import DiscordButton from "#lib/components/discord/DiscordButton.svelte";
    import DiscordContainer from "#lib/components/discord/DiscordContainer.svelte";
    import DiscordMarkdown from "#lib/components/discord/DiscordMarkdown.svelte";
    import DiscordMessage from "#lib/components/discord/DiscordMessage.svelte";
    import DiscordWindow from "#lib/components/discord/DiscordWindow.svelte";
    import { setGuildDiscord } from "#lib/discord/guild.svelte.ts";
    import { formatCount } from "#lib/format.ts";
    import type { Channel, Person } from "@square/api-client";
    import type { Draft } from "./board.ts";

    let { draft, guild, you, channels }: { draft: Draft; guild: string; you: Person; channels: Channel[] } = $props();

    setGuildDiscord(
        () => guild,
        () => [you],
    );

    const shown = $derived(Math.max(draft.threshold ?? 1, 1));

    const boardName = $derived(channels.find((channel) => channel.id === draft.channelId)?.name ?? "starboard");
    const source = $derived.by(() => {
        const texts = channels.filter((channel) => (channel.type === "text" || channel.type === "news") && channel.id !== draft.channelId);
        const picked = new Set(draft.channelIds);
        const allowed = texts.filter((channel) =>
            draft.channelMode === "only" ? picked.has(channel.id) : draft.channelMode === "except" ? !picked.has(channel.id) : true,
        );
        return allowed[0] ?? texts[0];
    });
    const posted = Math.floor(Date.now() / 1000) - 2 * 60 * 60;
    const footer = $derived(
        `-# ${draft.emojis[0] ?? "⭐"} **${formatCount(shown)}** · <@${you.id}> · <#${source?.id ?? draft.channelId}> · <t:${posted}:R>`,
    );
</script>

<DiscordWindow channel={boardName}>
    <DiscordMessage name={you.name} avatar={you.avatarUrl}>
        <DiscordAccessories>
            <DiscordContainer color={draft.color ?? "var(--color-embed-orange)"}>
                <DiscordMarkdown text="Just finished my desk setup, what do you all think?" />
                <DiscordMarkdown text={footer} />
            </DiscordContainer>
            <DiscordActionRow>
                <DiscordButton href="https://discord.com/channels/{guild}">Jump to message</DiscordButton>
            </DiscordActionRow>
        </DiscordAccessories>
    </DiscordMessage>
</DiscordWindow>
