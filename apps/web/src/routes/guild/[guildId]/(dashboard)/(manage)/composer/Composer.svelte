<script lang="ts">
    import { sortable } from "#lib/attachments/sortable.ts";
    import ConfirmDialog from "#lib/components/dashboard/ConfirmDialog.svelte";
    import PageHeading from "#lib/components/dashboard/PageHeading.svelte";
    import PageSkeleton from "#lib/components/dashboard/PageSkeleton.svelte";
    import PermissionNotice from "#lib/components/dashboard/PermissionNotice.svelte";
    import QueryGate from "#lib/components/dashboard/QueryGate.svelte";
    import SettingGroup from "#lib/components/dashboard/SettingGroup.svelte";
    import SettingRow from "#lib/components/dashboard/SettingRow.svelte";
    import UserPicker from "#lib/components/fields/UserPicker.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import EmptyState from "#lib/components/ui/EmptyState.svelte";
    import GuildIcon from "#lib/components/ui/GuildIcon.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Segmented from "#lib/components/ui/Segmented.svelte";
    import Select from "#lib/components/ui/Select.svelte";
    import { focusRing } from "#lib/components/ui/styles.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { errorMessage } from "#lib/errors.ts";
    import { bytes, formatCount } from "#lib/format.ts";
    import { SquarePermissions } from "#lib/permissions.ts";
    import { canUseAnyTextChannel, usableTextChannels } from "#lib/settings/options.ts";
    import * as settings from "#lib/settings/settings.remote.ts";
    import { load, save } from "#lib/storage.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import type { UserMatch } from "@square/api-client";
    import { flushSync, onDestroy } from "svelte";
    import { MediaQuery } from "svelte/reactivity";
    import MaterialSymbolsBadgeRounded from "~icons/material-symbols/badge-rounded";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";
    import MaterialSymbolsGroupRounded from "~icons/material-symbols/group-rounded";
    import MaterialSymbolsImageRounded from "~icons/material-symbols/image-rounded";
    import MaterialSymbolsSendRounded from "~icons/material-symbols/send-rounded";
    import MaterialSymbolsStackedEmailRounded from "~icons/material-symbols/stacked-email-rounded";
    import MaterialSymbolsTagRounded from "~icons/material-symbols/tag-rounded";
    import AddMenu from "./AddMenu.svelte";
    import BlockEditor from "./BlockEditor.svelte";
    import {
        copy,
        countOf,
        create,
        LIMITS,
        mediaOf,
        mediaUrls,
        NO_ROOM,
        problemOf,
        readFile,
        setComposer,
        textsOf,
        toComponents,
        Uploads,
        validUrl,
        type Block,
        type Container,
        type Draft,
        type Piece,
    } from "./composer.svelte.ts";
    import ComposerPreview from "./ComposerPreview.svelte";
    import { TOP_KINDS } from "./kinds.ts";
    import * as messages from "./messages.remote.ts";

    let {
        guild,
        user,
    }: {
        guild: { id: string; name: string; iconUrl: string | null };
        user: { name: string; avatarUrl: string | null } | null;
    } = $props();

    const channelsQuery = $derived(settings.guildChannels(guild.id));
    const rolesQuery = $derived(settings.guildRoles(guild.id));
    const senderQuery = $derived(messages.messageSender(guild.id));
    const permsQuery = $derived(settings.botPermissions(guild.id));
    const channels = $derived(channelsQuery.current ?? []);
    const perms = $derived(new SquarePermissions(permsQuery.current));
    const sender = $derived(senderQuery.current);

    const key = $derived(`square:composer:${guild.id}`);
    const EMPTY: Draft = { channelId: null, username: "", avatarUrl: "", blocks: [] };

    // A saved draft from an older build may not match today's shape, so anything odd starts fresh
    function restore(): Draft {
        try {
            const saved = JSON.parse(load(key) ?? "null") as Draft | null;
            if (saved && Array.isArray(saved.blocks) && typeof saved.username === "string" && typeof saved.avatarUrl === "string") return saved;
        } catch {
            return structuredClone(EMPTY);
        }
        return structuredClone(EMPTY);
    }

    // Kept in this browser only (uploads aren't), so a refresh doesn't lose a long message
    let draft = $state<Draft>(restore());
    $effect(() => {
        const json = JSON.stringify($state.snapshot(draft));
        const timer = setTimeout(() => save(key, json), 300);
        return () => clearTimeout(timer);
    });

    const sendChannels = $derived(usableTextChannels(channels, perms, "webhook", [draft.channelId]));

    const uploads = new Uploads();
    onDestroy(() => uploads.clear());

    const count = $derived(draft.blocks.reduce((sum, block) => sum + countOf(block), 0));
    const mediaCount = $derived(draft.blocks.reduce((sum, block) => sum + mediaOf(block), 0));
    const textLength = $derived(textsOf(draft.blocks).reduce((sum, text) => sum + text.length, 0));
    const used = $derived(
        [...new Set(mediaUrls(draft.blocks))].flatMap((url) => {
            const upload = uploads.of(url);
            return upload ? [upload] : [];
        }),
    );
    const usedBytes = $derived(used.reduce((sum, upload) => sum + upload.file.size, 0));
    const containers = $derived(draft.blocks.filter((block): block is Container => block.kind === "container"));
    const channelName = $derived(channels.find((channel) => channel.id === draft.channelId)?.name ?? "pick-a-channel");

    const nameError = $derived.by(() => {
        if (/discord|clyde/i.test(draft.username)) return "Discord doesn't allow “Discord” or “Clyde” in the name";
        if (/^(everyone|here)$/i.test(draft.username.trim())) return "Discord doesn't allow “everyone” or “here” as the name";
        return null;
    });
    const avatarError = $derived(draft.avatarUrl.trim() && !validUrl(draft.avatarUrl) ? "Use a full link starting with https://" : null);

    const problem = $derived.by(() => {
        if (!draft.channelId) return "Pick a channel to send to";
        if (!draft.blocks.length) return "Add something to send";
        if (count > LIMITS.components) return `A message has up to ${LIMITS.components} components`;
        if (mediaCount > LIMITS.media) return `A message shows up to ${LIMITS.media} pictures, videos and files`;
        if (textLength > LIMITS.text) return `A message has up to ${formatCount(LIMITS.text)} characters of text`;
        if (used.length > LIMITS.files) return `A message has up to ${LIMITS.files} files`;
        if (usedBytes > LIMITS.filesBytes) return `Files add up to more than ${bytes(LIMITS.filesBytes)}`;
        if (nameError) return nameError;
        if (avatarError) return "The avatar needs a full https:// link";
        return problemOf(draft.blocks, uploads.map);
    });

    function move(piece: Piece, to: Container | null) {
        const from = containers.find((container) => container.children.includes(piece));
        if (from) from.children.splice(from.children.indexOf(piece), 1);
        else draft.blocks.splice(draft.blocks.indexOf(piece), 1);
        if (to) to.children.push(piece);
        else draft.blocks.splice(from ? draft.blocks.indexOf(from) + 1 : draft.blocks.length, 0, piece);
    }

    setComposer({
        uploads,
        get guild() {
            return guild;
        },
        get room() {
            return LIMITS.components - count;
        },
        get mediaRoom() {
            return LIMITS.media - mediaCount;
        },
        full(block) {
            if (countOf(block) > LIMITS.components - count) return NO_ROOM.components;
            if (mediaOf(block) > LIMITS.media - mediaCount) return NO_ROOM.media;
            return null;
        },
        get containers() {
            return containers;
        },
        move,
        upload(file) {
            const limit = sender?.uploadLimit ?? LIMITS.filesBytes;
            if (file.size > limit) {
                toast.error(`${file.name} is too big`, { description: `Files can be up to ${bytes(limit)} in ${guild.name}.` });
                return null;
            }
            return uploads.add(file);
        },
    });

    function reorder(from: number, to: number) {
        flushSync(() => {
            const [moved] = draft.blocks.splice(from, 1);
            if (moved) draft.blocks.splice(to, 0, moved);
        });
    }

    // Discord's CDN serves any size, and search results only ask for small avatars
    function sized(url: string | null) {
        if (!url || !URL.canParse(url)) return url ?? "";
        const link = new URL(url);
        if (link.hostname === "cdn.discordapp.com") link.searchParams.set("size", "256");
        return link.href;
    }

    type Preset = { key: string; label: string; name: string; avatar: string; picture: string | null };
    let member = $state<UserMatch | null>(null);
    const presets = $derived(
        [
            { key: "square", label: sender?.name ?? "Square", name: "", avatar: "", picture: sender?.avatarUrl ?? null },
            { key: "server", label: "Server", name: guild.name.slice(0, LIMITS.name), avatar: sized(guild.iconUrl), picture: guild.iconUrl },
            user && { key: "you", label: "You", name: user.name, avatar: sized(user.avatarUrl), picture: user.avatarUrl },
            member && { key: member.id, label: member.name, name: member.name, avatar: sized(member.avatarUrl), picture: member.avatarUrl },
        ].filter((entry): entry is Preset => !!entry),
    );
    const isPreset = (entry: Preset) => draft.username === entry.name && draft.avatarUrl === entry.avatar;
    const presetAvatar = $derived(presets.some((entry) => entry.avatar === draft.avatarUrl));

    function usePreset(entry: Preset) {
        draft.username = entry.name;
        draft.avatarUrl = entry.avatar;
    }

    let sending = $state(false);
    async function send() {
        if (problem || !draft.channelId) return;
        sending = true;
        try {
            const files = await Promise.all(used.map(async (upload) => ({ name: upload.name, data: await readFile(upload.file) })));
            await messages.sendMessage({
                guild: guild.id,
                message: {
                    channelId: draft.channelId,
                    components: toComponents(draft.blocks),
                    username: draft.username.trim() || null,
                    avatarUrl: draft.avatarUrl.trim() || null,
                    files,
                },
            });
            toast.success("Message sent", { description: `It's in #${channelName} now.` });
        } catch (err) {
            toast.error("Square couldn't send that", { description: errorMessage(err, "Try again in a moment.") });
        } finally {
            sending = false;
        }
    }

    let clearing = $state(false);
    function clear() {
        uploads.clear();
        draft = { ...structuredClone(EMPTY), channelId: draft.channelId };
    }

    function add(kind: Block["kind"]) {
        draft.blocks.push(create(kind, mediaCount < LIMITS.media));
    }

    const wide = new MediaQuery("min-width: 1280px", false);
    let tab = $state<"editor" | "preview">("editor");
    const description = "Send a message with Components V2 through Square's webhook, under any name and avatar.";
</script>

<QueryGate queries={[channelsQuery, rolesQuery, senderQuery, permsQuery]} title="Composer" {description} actions>
    {#snippet skeleton()}<PageSkeleton groups={[{ rows: 3 }, { rows: 2 }]} />{/snippet}
    <div class="flex flex-col gap-6">
        <PageHeading title="Composer" {description}>
            {#snippet actions()}
                <Button
                    variant="ghost-danger"
                    disabled={!draft.blocks.length && !draft.username && !draft.avatarUrl}
                    onclick={() => (clearing = true)}
                >
                    <MaterialSymbolsCloseRounded />Clear
                </Button>
                <Tooltip content={problem}>
                    <Button variant="primary" loading={sending} disabled={!!problem || sending} onclick={send}>
                        {#if !sending}<MaterialSymbolsSendRounded />{/if}{sending ? "Sending…" : "Send"}
                    </Button>
                </Tooltip>
            {/snippet}
        </PageHeading>

        {#if !canUseAnyTextChannel(channels, perms, "webhook")}
            <PermissionNotice label="Square can't send messages here" permission="ManageWebhooks" kept="Your draft stays here until it does." />
        {/if}

        {#if !wide.current}
            <Segmented
                label="Show"
                class="w-fit"
                options={[
                    { value: "editor", label: "Editor" },
                    { value: "preview", label: "Preview" },
                ]}
                bind:value={tab}
            />
        {/if}

        <div class="grid grid-cols-1 items-start gap-6 xl:grid-cols-2">
            <div class={["flex min-w-0 flex-col gap-6", !wide.current && tab !== "editor" && "hidden"]}>
                <SettingGroup title="Sender">
                    <SettingRow label="Channel" description="Where the message goes." icon={MaterialSymbolsTagRounded}>
                        <Select
                            title="Channel"
                            placeholder="Pick a channel"
                            options={sendChannels.options}
                            note={sendChannels.note}
                            bind:value={draft.channelId}
                        />
                    </SettingRow>
                    <SettingRow label="Preset" description="Fill in the name and avatar in one go." icon={MaterialSymbolsGroupRounded} layout="below">
                        <div class="flex flex-wrap items-center gap-2">
                            {#each presets as entry (entry.key)}
                                <button
                                    type="button"
                                    aria-pressed={isPreset(entry)}
                                    class={[
                                        "ripple flex h-12 max-w-full items-center gap-2 rounded-control-lg bg-gray-800 pr-4 pl-1 text-sm font-medium transition-colors hover:bg-gray-700 md:h-10 md:rounded-2xl md:pr-3",
                                        "aria-pressed:bg-accent/10 aria-pressed:text-accent",
                                        focusRing,
                                    ]}
                                    onclick={() => usePreset(entry)}
                                >
                                    {#if entry.key === "server"}
                                        <GuildIcon
                                            src={entry.picture}
                                            name={guild.name}
                                            class="size-10 shrink-0 rounded-2xl md:size-8 md:rounded-xl"
                                        />
                                    {:else}
                                        <Avatar src={entry.picture} name={entry.label} class="size-10 shrink-0 md:size-8" />
                                    {/if}
                                    <span class="truncate">{entry.label}</span>
                                </button>
                            {/each}
                            <UserPicker
                                guild={guild.id}
                                title="Use a member"
                                placeholder="Use a member"
                                exclude={[member?.id ?? ""]}
                                onpick={(picked) => {
                                    member = picked;
                                    draft.username = picked.name.slice(0, LIMITS.name);
                                    draft.avatarUrl = sized(picked.avatarUrl);
                                }}
                                class="w-full md:w-60"
                            />
                        </div>
                    </SettingRow>
                    <SettingRow label="Name" description="Left empty, it's {sender?.name ?? 'Square'}." icon={MaterialSymbolsBadgeRounded}>
                        <Input
                            aria-label="Name"
                            placeholder={sender?.name ?? "Square"}
                            maxlength={LIMITS.name}
                            error={nameError}
                            bind:value={draft.username}
                        />
                    </SettingRow>
                    <SettingRow
                        label="Avatar"
                        description="Left empty, it's {sender?.name ?? 'Square'}'s. Any image link works."
                        icon={MaterialSymbolsImageRounded}
                    >
                        <div class="flex w-full items-center gap-2">
                            <Avatar
                                src={draft.avatarUrl.trim() && !avatarError ? draft.avatarUrl.trim() : (sender?.avatarUrl ?? null)}
                                name={draft.username || "Square"}
                                class="size-12 shrink-0 md:size-10"
                            />
                            <Input
                                type="url"
                                aria-label="Avatar link"
                                placeholder={presetAvatar && draft.avatarUrl ? "Set by the preset" : "https:// link to an image"}
                                maxlength={2048}
                                error={avatarError}
                                bind:value={() => (presetAvatar ? "" : draft.avatarUrl), (value) => (draft.avatarUrl = value)}
                            />
                        </div>
                    </SettingRow>
                </SettingGroup>

                <section class="flex flex-col gap-2">
                    <div class="flex flex-wrap items-end gap-x-4 gap-y-2 px-2">
                        <div class="flex min-w-60 flex-1 flex-col">
                            <h2 class="font-display text-lg font-semibold">Message</h2>
                            <p class="text-sm text-gray-400">Drag to reorder. Move pieces in and out of containers from their menu.</p>
                        </div>
                        <div class="flex shrink-0 gap-4 font-mono text-xs text-gray-400">
                            <span class={[count > LIMITS.components && "text-red-400"]}>{count}/{LIMITS.components} parts</span>
                            <span class={[textLength > LIMITS.text && "text-red-400"]}
                                >{formatCount(textLength)}/{formatCount(LIMITS.text)} chars</span
                            >
                            {#if mediaCount}<span class={[mediaCount > LIMITS.media && "text-red-400"]}>{mediaCount}/{LIMITS.media} media</span>{/if}
                            {#if used.length}<span class={[used.length > LIMITS.files && "text-red-400"]}>{used.length}/{LIMITS.files} files</span
                                >{/if}
                        </div>
                    </div>
                    {#if draft.blocks.length}
                        <ol class="flex flex-col gap-2" {@attach sortable({ onmove: reorder })}>
                            {#each draft.blocks as block, index (block.id)}
                                <BlockEditor
                                    {block}
                                    {index}
                                    onremove={() => draft.blocks.splice(index, 1)}
                                    onduplicate={() => draft.blocks.splice(index + 1, 0, copy($state.snapshot(block)))}
                                />
                            {/each}
                        </ol>
                    {:else}
                        <EmptyState
                            card
                            icon={MaterialSymbolsStackedEmailRounded}
                            title="Nothing here yet"
                            text="Start with a container or some text, then add pictures and invite buttons."
                        />
                    {/if}
                    <AddMenu kinds={TOP_KINDS} onadd={add} />
                </section>
            </div>

            <aside class={["flex min-w-0 flex-col gap-4 xl:sticky xl:top-0", !wide.current && tab !== "preview" && "hidden"]}>
                <h2 class="px-2 font-display text-lg font-semibold">Preview</h2>
                <ComposerPreview
                    blocks={draft.blocks}
                    name={draft.username.trim() || sender?.name || "Square"}
                    avatar={draft.avatarUrl.trim() && !avatarError ? draft.avatarUrl.trim() : (sender?.avatarUrl ?? "")}
                    channel={channelName}
                />
            </aside>
        </div>
    </div>
</QueryGate>

<ConfirmDialog
    bind:open={clearing}
    title="Clear this message?"
    description="Every component, upload, name and avatar goes. The channel stays picked."
    label="Clear"
    done="Message cleared"
    run={async () => clear()}
/>
