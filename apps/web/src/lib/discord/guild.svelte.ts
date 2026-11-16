import { setDiscord, type DiscordContext } from "#lib/discord/context.ts";
import { guildChannels, guildRoles, mentionedChannel, mentionedUser } from "#lib/settings/settings.remote.ts";

const ID = /^\d{17,20}$/;
const VOICE = new Set(["voice", "stage_voice"]);

export type GuildLookups = Pick<DiscordContext, "user" | "role" | "channel">;

// Call during component setup, since it creates $derived state
export function guildLookups(guild: () => string, known: () => { id: string; name: string }[] = () => []): GuildLookups {
    const roles = $derived(
        Object.fromEntries((guildRoles(guild()).current ?? []).map((role) => [role.id, { name: role.name, color: role.color ?? undefined }])),
    );
    const channels = $derived(
        Object.fromEntries(
            (guildChannels(guild()).current ?? []).map((channel) => [channel.id, { name: channel.name, voice: VOICE.has(channel.type) }]),
        ),
    );
    const people = $derived(Object.fromEntries(known().map((person) => [person.id, person])));

    return {
        user: (id) => people[id] ?? (ID.test(id) ? mentionedUser({ guild: guild(), id }).current : null),
        role: (id) => roles[id],
        channel: (id) => {
            if (channels[id] || !ID.test(id)) return channels[id];
            const found = mentionedChannel({ guild: guild(), id }).current;
            if (!found) return found;
            const outside = found.guildId !== guild() ? { name: found.guildName, iconUrl: found.guildIconUrl } : undefined;
            return { name: found.name, voice: VOICE.has(found.type), guild: outside };
        },
    };
}

export function setGuildDiscord(guild: () => string, known?: () => { id: string; name: string }[]) {
    setDiscord({ ...guildLookups(guild, known), fileUrl: (file) => file.url });
}
