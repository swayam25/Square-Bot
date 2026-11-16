<script lang="ts">
    import PageHeading from "#lib/components/dashboard/PageHeading.svelte";
    import PageSkeleton from "#lib/components/dashboard/PageSkeleton.svelte";
    import QueryGate from "#lib/components/dashboard/QueryGate.svelte";
    import ResetButton from "#lib/components/dashboard/ResetButton.svelte";
    import SaveBar from "#lib/components/dashboard/SaveBar.svelte";
    import SettingGroup from "#lib/components/dashboard/SettingGroup.svelte";
    import SettingRow from "#lib/components/dashboard/SettingRow.svelte";
    import DiscordMessage from "#lib/components/discord/DiscordMessage.svelte";
    import DiscordProfile from "#lib/components/discord/DiscordProfile.svelte";
    import DiscordWindow from "#lib/components/discord/DiscordWindow.svelte";
    import DiscordTextField from "#lib/components/fields/DiscordTextField.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { setGuildDiscord } from "#lib/discord/guild.svelte.ts";
    import MaterialSymbolsBadgeRounded from "~icons/material-symbols/badge-rounded";
    import MaterialSymbolsImageRounded from "~icons/material-symbols/image-rounded";
    import MaterialSymbolsNotesRounded from "~icons/material-symbols/notes-rounded";
    import MaterialSymbolsWallpaperRounded from "~icons/material-symbols/wallpaper-rounded";
    import type { PageProps } from "./$types";
    import ImageField from "./ImageField.svelte";
    import * as profile from "./profile.remote.ts";
    import { BIO_MAX, IMAGE_MAX_BYTES, NICK_MAX } from "./profile.ts";

    let { data }: PageProps = $props();

    const guild = $derived(data.guild.id);
    setGuildDiscord(() => guild);
    const savedQuery = $derived(profile.botProfile(guild));
    const saved = $derived(savedQuery.current!);

    let nick = $derived(saved.nick ?? "");
    let bio = $derived(saved.bio ?? "");
    let avatar = $derived<string | null>(saved.avatarUrl);
    let banner = $derived<string | null>(saved.bannerUrl);

    const nickValue = $derived(nick.trim() || null);
    const bioValue = $derived(bio.trim() || null);

    const changes = $derived({
        ...(nickValue !== saved.nick && { nick: nickValue }),
        ...(bioValue !== saved.bio && { bio: bioValue }),
        ...(avatar !== saved.avatarUrl && { avatar }),
        ...(banner !== saved.bannerUrl && { banner }),
    });

    function discard() {
        nick = saved.nick ?? "";
        bio = saved.bio ?? "";
        avatar = saved.avatarUrl;
        banner = saved.bannerUrl;
    }

    const isDefault = $derived(!saved.nick && !saved.bio && !saved.avatarUrl && !saved.bannerUrl);
    const imageLimit = `PNG, JPEG or GIF up to ${IMAGE_MAX_BYTES / 1024 / 1024} MB.`;
</script>

<QueryGate queries={[savedQuery]} title="Customize" description="How Square looks in {data.guild.name}." actions>
    {#snippet skeleton()}<PageSkeleton groups={[{ rows: 4, title: false }]} />{/snippet}
    <div class="flex flex-col gap-6">
        <PageHeading title="Customize" description="How Square looks in {data.guild.name}.">
            {#snippet actions()}
                <ResetButton
                    title="Reset Square's profile here?"
                    done="Profile reset"
                    description="Square goes back to its usual name, avatar, banner and bio in {data.guild.name}."
                    disabled={isDefault}
                    reset={() => profile.resetBotProfile(guild)}
                    apply={(next) => savedQuery.set(next)}
                />
            {/snippet}
        </PageHeading>

        <div class="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
            <SettingGroup>
                <SettingRow label="Nickname" description="Shown instead of {saved.name} in this server." icon={MaterialSymbolsBadgeRounded}>
                    <Tooltip content={saved.canNick ? null : "Square needs the Change Nickname permission here"} class="w-full">
                        <Input aria-label="Nickname" placeholder={saved.name} maxlength={NICK_MAX} disabled={!saved.canNick} bind:value={nick} />
                    </Tooltip>
                </SettingRow>
                <SettingRow
                    label="Bio"
                    description={saved.globalBio ? "Left empty, Square's usual About me shows." : "The About me people see on Square's profile here."}
                    icon={MaterialSymbolsNotesRounded}
                    layout="below"
                >
                    <DiscordTextField
                        aria-label="Bio"
                        placeholder={saved.globalBio ?? "What Square does in this server"}
                        maxlength={BIO_MAX}
                        guild={data.guild}
                        bind:value={bio}
                    />
                </SettingRow>
                <SettingRow label="Avatar" description="{imageLimit} Without one, Square uses its usual avatar." icon={MaterialSymbolsImageRounded}>
                    <ImageField kind="avatar" name={nickValue ?? saved.name} fallback={saved.globalAvatarUrl} bind:value={avatar} />
                </SettingRow>
                <SettingRow
                    label="Banner"
                    description="{imageLimit} Shown at the top of the profile, best at 5:2."
                    icon={MaterialSymbolsWallpaperRounded}
                >
                    <ImageField
                        kind="banner"
                        name={nickValue ?? saved.name}
                        fallback={saved.globalBannerUrl}
                        color={saved.bannerColor}
                        bind:value={banner}
                    />
                </SettingRow>
            </SettingGroup>

            <aside class="@container flex flex-col gap-4 xl:sticky xl:top-0">
                <h2 class="px-2 font-display text-lg font-semibold">Preview</h2>
                <div class="grid items-start gap-4 @2xl:grid-cols-2">
                    <DiscordProfile
                        name={nickValue ?? saved.name}
                        avatar={avatar ?? saved.globalAvatarUrl}
                        banner={banner ?? saved.globalBannerUrl}
                        color={saved.bannerColor}
                        bio={bioValue ?? saved.globalBio}
                    />
                    <DiscordWindow channel="general">
                        <DiscordMessage name={nickValue ?? saved.name} avatar={avatar ?? saved.globalAvatarUrl}>
                            <p>Ready when you are.</p>
                        </DiscordMessage>
                    </DiscordWindow>
                </div>
            </aside>
        </div>
    </div>

    <SaveBar dirty={Object.keys(changes).length > 0} onsave={() => profile.updateBotProfile({ guild, ...changes })} ondiscard={discard} />
</QueryGate>
