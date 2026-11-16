<script lang="ts">
    import DiscordAccessories from "#lib/components/discord/DiscordAccessories.svelte";
    import DiscordActionRow from "#lib/components/discord/DiscordActionRow.svelte";
    import DiscordButton from "#lib/components/discord/DiscordButton.svelte";
    import DiscordContainer from "#lib/components/discord/DiscordContainer.svelte";
    import DiscordEmoji from "#lib/components/discord/DiscordEmoji.svelte";
    import DiscordGallery from "#lib/components/discord/DiscordGallery.svelte";
    import DiscordMarkdown from "#lib/components/discord/DiscordMarkdown.svelte";
    import DiscordMessage from "#lib/components/discord/DiscordMessage.svelte";
    import DiscordWindow from "#lib/components/discord/DiscordWindow.svelte";
    import { setGuildDiscord } from "#lib/discord/guild.svelte.ts";
    import { EMOJI } from "#lib/discord/markdown.ts";
    import { formatCount } from "#lib/format.ts";
    import type { Channel, Person } from "@square/api-client";
    import type { Component } from "svelte";
    import MaterialSymbolsAdd2Rounded from "~icons/material-symbols/add-2-rounded";
    import MaterialSymbolsBookmarkRounded from "~icons/material-symbols/bookmark-rounded";
    import MaterialSymbolsCelebrationRounded from "~icons/material-symbols/celebration-rounded";
    import MaterialSymbolsCrownRounded from "~icons/material-symbols/crown-rounded";
    import MaterialSymbolsGroupsRounded from "~icons/material-symbols/groups-rounded";
    import MaterialSymbolsHistoryRounded from "~icons/material-symbols/history-rounded";
    import MaterialSymbolsLinkRounded from "~icons/material-symbols/link-rounded";
    import MaterialSymbolsPasskeyRounded from "~icons/material-symbols/passkey-rounded";
    import MaterialSymbolsPersonRounded from "~icons/material-symbols/person-rounded";
    import { validUrl, type Draft, type GiveawayStatus } from "./giveaway.ts";

    let {
        draft,
        status,
        guild,
        invites = true,
        you,
        channels,
        entries = 0,
        winners = [],
        endedAt = null,
        storedImage = null,
    }: {
        draft: Draft;
        status: GiveawayStatus | "new";
        guild: string;
        invites?: boolean;
        you: Person;
        channels: Channel[];
        entries?: number;
        winners?: Person[];
        endedAt?: number | null;
        storedImage?: string | null;
    } = $props();

    const image = $derived(
        draft.imageUpload?.dataUrl ??
            (draft.imageFile ? storedImage : null) ??
            (!draft.imageFile && validUrl(draft.imageUrl) ? draft.imageUrl.trim() : null),
    );

    const host = $derived(draft.host ?? you);
    const ended = $derived(status === "ended");

    setGuildDiscord(
        () => guild,
        () => [host, ...winners],
    );

    const role = (id: string) => (id === guild ? "@everyone" : `<@&${id}>`);
    const roleList = (ids: string[]) => ids.map(role).join(", ");
    const days = (count: number) => `\`${count} day${count === 1 ? "" : "s"}\``;
    const seconds = (ms: number) => Math.floor(ms / 1000);

    type Line = { icon: Component; text: string; color?: string };
    const lines = $derived.by<Line[]>(() => {
        if (ended) {
            const who = winners.length ? winners.map((person) => `<@${person.id}>`).join(", ") : "Nobody could win";
            return [
                { icon: MaterialSymbolsCrownRounded, text: `**${winners.length === 1 ? "Winner" : "Winners"}**: ${who}`, color: "text-embed-orange" },
                { icon: MaterialSymbolsPersonRounded, text: `**Hosted By**: <@${host.id}>` },
                { icon: MaterialSymbolsHistoryRounded, text: `**Ended**: <t:${seconds(endedAt ?? draft.endsAt ?? Date.now())}:R>` },
            ];
        }
        const ends = seconds(draft.endsAt ?? Date.now());
        const result: Line[] = [
            { icon: MaterialSymbolsHistoryRounded, text: `**Ends**: <t:${ends}:R>` },
            { icon: MaterialSymbolsCrownRounded, text: `**Winners**: \`${draft.winnerCount ?? 1}\``, color: "text-embed-orange" },
            { icon: MaterialSymbolsPersonRounded, text: `**Hosted By**: <@${host.id}>` },
        ];
        const required = draft.requiredRoleIds;
        if (required.length) {
            const label = required.length === 1 ? "Needs" : draft.requireAllRoles ? "Needs All Of" : "Needs One Of";
            result.push({ icon: MaterialSymbolsBookmarkRounded, text: `**${label}**: ${roleList(required)}` });
        }
        if (draft.blockedRoleIds.length) result.push({ icon: MaterialSymbolsPasskeyRounded, text: `**Not For**: ${roleList(draft.blockedRoleIds)}` });
        if (draft.minAccountDays)
            result.push({ icon: MaterialSymbolsPersonRounded, text: `**Account Age**: at least ${days(draft.minAccountDays)}` });
        if (draft.minMemberDays)
            result.push({ icon: MaterialSymbolsGroupsRounded, text: `**In Server For**: at least ${days(draft.minMemberDays)}` });
        if (invites && draft.minInvites)
            result.push({
                icon: MaterialSymbolsLinkRounded,
                text: `**Invites**: at least \`${draft.minInvites}\` invite${draft.minInvites === 1 ? "" : "s"}`,
            });
        const bonus = draft.bonusRoles.filter((entry) => entry.roleId && entry.entries);
        if (bonus.length) {
            const text = bonus.map((entry) => `${role(entry.roleId!)} \`+${entry.entries}\``).join(", ");
            result.push({ icon: MaterialSymbolsAdd2Rounded, text: `**Bonus Entries**: ${text}` });
        }
        return result;
    });

    const buttonStyle = $derived(({ blurple: "primary", green: "success", grey: "secondary", red: "danger" } as const)[draft.buttonStyle]);
    const label = $derived(draft.buttonLabel.trim() ? `${draft.buttonLabel.trim()} · ${formatCount(entries)}` : formatCount(entries));
    const emoji = $derived.by(() => {
        const custom = /^<(a?):(\w+):(\d{17,20})>$/.exec(draft.buttonEmoji ?? "");
        return custom ? { name: custom[2]!, id: custom[3]!, animated: custom[1] === "a" } : null;
    });
    const channelName = $derived(channels.find((entry) => entry.id === draft.channelId)?.name ?? "giveaways");
</script>

<DiscordWindow channel={channelName}>
    <DiscordMessage>
        <DiscordAccessories>
            {#if draft.pingRoleId && !ended}<DiscordMarkdown text={role(draft.pingRoleId)} />{/if}
            <DiscordContainer color={draft.color}>
                <DiscordMarkdown text="## {draft.prize.trim() || 'Your prize'}" />
                {#if draft.description.trim()}<DiscordMarkdown text={draft.description} />{/if}
                <div class="wrap-anywhere">
                    {#each lines as line, index (index)}
                        <p><line.icon class={[EMOJI, line.color ?? "text-accent"]} /> <DiscordMarkdown inline text={line.text} /></p>
                    {/each}
                </div>
                {#if image}
                    <DiscordGallery files={[{ name: "image", url: image, kind: "image" }]} missing="Discord can't load this image" />
                {/if}
            </DiscordContainer>
            <DiscordActionRow>
                <DiscordButton style={buttonStyle} disabled={ended}>
                    {#if emoji}
                        <DiscordEmoji {...emoji} tooltip={false} />
                    {:else if draft.buttonEmoji}
                        <DiscordEmoji name={draft.buttonEmoji} />
                    {:else}
                        <MaterialSymbolsCelebrationRounded class="size-[1.375em]" />
                    {/if}
                    <span>{label}</span>
                </DiscordButton>
            </DiscordActionRow>
        </DiscordAccessories>
    </DiscordMessage>
</DiscordWindow>
