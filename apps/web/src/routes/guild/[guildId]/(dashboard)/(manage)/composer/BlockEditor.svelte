<script lang="ts">
    import { sortable } from "#lib/attachments/sortable.ts";
    import Button from "#lib/components/ui/Button.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Popup from "#lib/components/ui/Popup.svelte";
    import Segmented from "#lib/components/ui/Segmented.svelte";
    import { focusRing } from "#lib/components/ui/styles.ts";
    import Textarea from "#lib/components/ui/Textarea.svelte";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { plural } from "#lib/format.ts";
    import { mobile } from "#lib/media.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { flushSync } from "svelte";
    import { slide } from "svelte/transition";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";
    import MaterialSymbolsContentCopyRounded from "~icons/material-symbols/content-copy-rounded";
    import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
    import MaterialSymbolsDragIndicatorRounded from "~icons/material-symbols/drag-indicator-rounded";
    import MaterialSymbolsDriveFileMoveRounded from "~icons/material-symbols/drive-file-move-rounded";
    import MaterialSymbolsHorizontalRuleRounded from "~icons/material-symbols/horizontal-rule-rounded";
    import MaterialSymbolsKeyboardArrowDownRounded from "~icons/material-symbols/keyboard-arrow-down-rounded";
    import MaterialSymbolsUploadRounded from "~icons/material-symbols/upload-rounded";
    import MaterialSymbolsVisibilityOffRounded from "~icons/material-symbols/visibility-off-rounded";
    import AddMenu from "./AddMenu.svelte";
    import BlockEditor from "./BlockEditor.svelte";
    import ButtonField from "./ButtonField.svelte";
    import {
        accepts,
        copy,
        create,
        getComposer,
        LABELS,
        LIMITS,
        linkButton,
        media,
        MEDIA_TYPES,
        NO_ROOM,
        pickFiles,
        uid,
        type Block,
        type Container,
        type Piece,
    } from "./composer.svelte.ts";
    import { INNER_KINDS, KINDS } from "./kinds.ts";
    import MediaField from "./MediaField.svelte";
    import OptionChip from "./OptionChip.svelte";

    let {
        block,
        index,
        parent = null,
        onremove,
        onduplicate,
    }: {
        block: Block;
        index: number;
        parent?: Container | null;
        onremove: () => void;
        onduplicate: () => void;
    } = $props();

    const composer = getComposer();
    const Icon = $derived(KINDS[block.kind].icon);
    const name = $derived(`${LABELS[block.kind]} ${index + 1}`);
    let open = $state(true);
    // Empty fields only turn red once someone has left them
    let touched = $state<Record<string, boolean>>({});
    const emptyError = (id: string, text: string) => (touched[id] && !text.trim() ? "Text can't be empty" : null);

    const COLORS = [
        { name: "Square", value: "#1fceec" },
        { name: "Blurple", value: "#5865f2" },
        { name: "Green", value: "#57f287" },
        { name: "Yellow", value: "#fee75c" },
        { name: "Red", value: "#ed4245" },
        { name: "Fuchsia", value: "#eb459e" },
    ];

    const firstLine = (text: string) => text.trim().split("\n")[0] ?? "";

    const summary = $derived.by(() => {
        switch (block.kind) {
            case "container":
                return plural(block.children.length, "piece");
            case "text":
                return firstLine(block.text);
            case "section":
                return firstLine(block.texts[0]?.text ?? "");
            case "gallery":
                return plural(block.items.length, "item");
            case "file":
                return composer.uploads.of(block.url)?.name ?? "";
            case "separator":
                return `${block.divider ? "Line" : "No line"}, ${block.large ? "large" : "small"} gap`;
            case "row":
                return plural(block.buttons.length, "button");
        }
    });

    // `sortable` measures the drop right after this returns, so the list must already be in its new order
    function reorder<T>(list: T[]) {
        return (from: number, to: number) =>
            flushSync(() => {
                const [moved] = list.splice(from, 1);
                if (moved !== undefined) list.splice(to, 0, moved);
            });
    }

    let hex = $derived(block.kind === "container" ? (block.color ?? "") : "");
    function setHex(value: string) {
        if (block.kind !== "container") return;
        hex = value;
        const clean = value.trim().replace(/^#?/, "#").toLowerCase();
        if (!value.trim()) block.color = null;
        else if (/^#[0-9a-f]{6}$/.test(clean)) block.color = clean;
    }

    async function uploadMany() {
        if (block.kind !== "gallery") return;
        const filled = block.items.filter((item) => item.url).length;
        // Empty items get replaced, so they free their media slot
        const room = Math.min(LIMITS.galleryItems - filled, composer.mediaRoom + block.items.length - filled);
        const files = (await pickFiles(MEDIA_TYPES, true)).filter((file) => accepts(file, MEDIA_TYPES));
        if (files.length > room)
            toast.warning(`Only ${plural(room, "more item")} fit${room < LIMITS.galleryItems - filled ? " in this message" : " in this gallery"}`);
        const links = files
            .slice(0, room)
            .map((file) => composer.upload(file))
            .filter((link) => link !== null);
        const kept = block.items.filter((item) => item.url);
        block.items = [...kept, ...links.map((link) => media(link))];
        if (!block.items.length) block.items = [media()];
    }

    const handle =
        "flex h-10 w-8 shrink-0 cursor-grab touch-none items-center justify-center rounded-xl text-gray-400 hover:text-gray-50 active:cursor-grabbing";
    const sortableItem = "rounded-2xl data-dragging:z-10 data-dragging:bg-gray-800 data-dragging:shadow-xl data-dragging:shadow-black/50";
</script>

{#snippet dragHandle(label: string)}
    <Tooltip content={label}>
        <button type="button" data-drag-handle class={[handle, focusRing]}><MaterialSymbolsDragIndicatorRounded class="size-5" /></button>
    </Tooltip>
{/snippet}

{#snippet remove(label: string, onclick: () => void, clear = false)}
    <Tooltip content={label}>
        <Button icon variant={clear ? "ghost" : "ghost-danger"} {onclick}>
            {#if clear}<MaterialSymbolsCloseRounded />{:else}<MaterialSymbolsDeleteRounded />{/if}
        </Button>
    </Tooltip>
{/snippet}

<li
    data-sortable-index={index}
    class={[
        "flex flex-col rounded-3xl data-dragging:z-10 data-dragging:shadow-2xl data-dragging:shadow-black/60",
        parent ? "bg-gray-950 data-dragging:bg-gray-900" : "bg-gray-900 data-dragging:bg-gray-800",
    ]}
    style:box-shadow={block.kind === "container" && block.color ? `inset 4px 0 ${block.color}` : undefined}
>
    <div class="flex items-center gap-1 p-2">
        {@render dragHandle("Drag to reorder")}
        <button
            type="button"
            aria-expanded={open}
            class={["flex min-w-0 flex-1 cursor-pointer items-center gap-2 rounded-xl py-2 text-left", focusRing]}
            onclick={() => (open = !open)}
        >
            <Icon class="size-5 shrink-0 text-accent" />
            <span class="shrink-0 text-sm font-semibold">{name}</span>
            {#if summary}<span class="truncate text-sm text-gray-400">{summary}</span>{/if}
        </button>
        {#if block.kind !== "container" && (composer.containers.length > (parent ? 1 : 0) || parent)}
            <Tooltip content="Move">
                <Popup
                    title="Move {name}"
                    placement="bottom-end"
                    contentClass="w-64"
                    triggerClass={[
                        "flex size-12 shrink-0 items-center justify-center rounded-full text-gray-400 hover:bg-gray-800 hover:text-gray-100 md:size-10",
                        focusRing,
                    ]}
                >
                    {#snippet trigger()}<MaterialSymbolsDriveFileMoveRounded class="size-5" />{/snippet}
                    <div class={["flex flex-col gap-1", mobile.current && "px-4 pb-4"]}>
                        {#if parent}
                            <button
                                type="button"
                                class="ripple flex h-10 items-center rounded-xl px-4 text-left text-sm font-medium hover:bg-white/10"
                                onclick={() => composer.move(block as Piece, null)}
                            >
                                Out of the container
                            </button>
                        {/if}
                        {#each composer.containers as container, at (container.id)}
                            {#if container !== parent}
                                <button
                                    type="button"
                                    class="ripple flex h-10 items-center gap-2 rounded-xl px-4 text-left text-sm font-medium hover:bg-white/10"
                                    onclick={() => composer.move(block as Piece, container)}
                                >
                                    <span class="size-3 shrink-0 rounded-full bg-gray-600" style:background-color={container.color ?? undefined}
                                    ></span>
                                    Into container {at + 1}
                                </button>
                            {/if}
                        {/each}
                    </div>
                </Popup>
            </Tooltip>
        {/if}
        <Tooltip content={composer.full(block) ?? "Duplicate"}>
            <Button icon variant="ghost" disabled={!!composer.full(block)} onclick={onduplicate}><MaterialSymbolsContentCopyRounded /></Button>
        </Tooltip>
        <Tooltip content="Delete">
            <Button icon variant="ghost-danger" onclick={onremove}><MaterialSymbolsDeleteRounded /></Button>
        </Tooltip>
        <Tooltip content={open ? "Collapse" : "Expand"}>
            <Button icon variant="ghost" aria-expanded={open} onclick={() => (open = !open)}>
                <MaterialSymbolsKeyboardArrowDownRounded class={["transition-transform duration-200", open && "rotate-180"]} />
            </Button>
        </Tooltip>
    </div>

    {#if open}
        <div transition:slide={{ duration: 200 }} class="flex flex-col gap-4 px-4 pb-4">
            {#if block.kind === "container"}
                <div class="flex flex-wrap items-center gap-2">
                    <label
                        class={[
                            "relative size-12 shrink-0 cursor-pointer overflow-hidden rounded-full bg-gray-800 md:size-10",
                            "has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-accent",
                        ]}
                        style:background-color={block.color ?? undefined}
                    >
                        <input
                            type="color"
                            aria-label="Accent color"
                            class="absolute inset-0 size-full cursor-pointer opacity-0"
                            value={block.color ?? "#1fceec"}
                            oninput={(event) => setHex(event.currentTarget.value)}
                        />
                    </label>
                    <Input
                        aria-label="Accent color hex"
                        placeholder="No color"
                        maxlength={7}
                        class="w-32!"
                        error={hex.trim() && hex.trim().replace(/^#?/, "#").toLowerCase() !== block.color ? "Use a hex color like #1FCEEC" : null}
                        bind:value={() => hex, setHex}
                    />
                    {#each COLORS as color (color.value)}
                        <Tooltip content={color.name}>
                            <button
                                type="button"
                                aria-pressed={block.color === color.value}
                                class={[
                                    "size-8 shrink-0 cursor-pointer rounded-full transition-transform hover:scale-110 aria-pressed:scale-110",
                                    focusRing,
                                ]}
                                style:background-color={color.value}
                                onclick={() => setHex(color.value)}
                            >
                                <span class="sr-only">{color.name}</span>
                            </button>
                        </Tooltip>
                    {/each}
                    {#if block.color}
                        {@render remove("No color", () => setHex(""), true)}
                    {/if}
                    <span class="ml-auto"
                        ><OptionChip icon={MaterialSymbolsVisibilityOffRounded} bind:pressed={block.spoiler}>Spoiler</OptionChip></span
                    >
                </div>
                <ol class="flex flex-col gap-2" {@attach sortable({ onmove: reorder(block.children) })}>
                    {#each block.children as child, at (child.id)}
                        <BlockEditor
                            block={child}
                            index={at}
                            parent={block}
                            onremove={() => block.kind === "container" && block.children.splice(at, 1)}
                            onduplicate={() => block.kind === "container" && block.children.splice(at + 1, 0, copy($state.snapshot(child)))}
                        />
                    {/each}
                </ol>
                <AddMenu
                    kinds={INNER_KINDS}
                    label="Add to container"
                    onadd={(kind) => block.kind === "container" && block.children.push(create(kind, composer.mediaRoom > 0) as Piece)}
                />
            {:else if block.kind === "text"}
                <Textarea
                    aria-label="Text"
                    placeholder="Markdown, mentions and emojis work here"
                    maxlength={LIMITS.text}
                    emojis={composer.guild}
                    error={emptyError(block.id, block.text)}
                    onblur={() => (touched[block.id] = true)}
                    bind:value={block.text}
                />
            {:else if block.kind === "section"}
                <ol class="flex flex-col gap-2" {@attach sortable({ onmove: reorder(block.texts) })}>
                    {#each block.texts as entry, at (entry.id)}
                        <li data-sortable-index={at} class={["flex items-start gap-1", sortableItem]}>
                            {#if block.texts.length > 1}<span class="pt-1">{@render dragHandle("Drag to reorder")}</span>{/if}
                            <Textarea
                                aria-label="Text {at + 1}"
                                placeholder="Text {at + 1}"
                                maxlength={LIMITS.text}
                                emojis={composer.guild}
                                error={emptyError(entry.id, entry.text)}
                                onblur={() => (touched[entry.id] = true)}
                                bind:value={entry.text}
                            />
                            {#if block.texts.length > 1}
                                <span class="pt-1">{@render remove("Remove text", () => block.kind === "section" && block.texts.splice(at, 1))}</span>
                            {/if}
                        </li>
                    {/each}
                </ol>
                {#if block.texts.length < LIMITS.sectionTexts}
                    <Tooltip content={composer.room < 1 ? NO_ROOM.components : null} class="w-fit">
                        <Button
                            size="sm"
                            disabled={composer.room < 1}
                            onclick={() => block.kind === "section" && block.texts.push({ id: uid(), text: "" })}
                        >
                            <MaterialSymbolsAddRounded />Add text
                        </Button>
                    </Tooltip>
                {/if}
                <div class="flex flex-col gap-2">
                    <Segmented
                        label="Beside the text"
                        class="w-fit"
                        options={[
                            {
                                value: "thumbnail",
                                label: "Thumbnail",
                                disabled: block.accessory.kind === "button" && composer.mediaRoom < 1 && NO_ROOM.media,
                            },
                            { value: "button", label: "Button" },
                        ]}
                        bind:value={
                            () => (block.kind === "section" ? block.accessory.kind : "thumbnail"),
                            (kind) => {
                                if (block.kind !== "section" || block.accessory.kind === kind) return;
                                block.accessory = kind === "button" ? linkButton() : { id: uid(), kind: "thumbnail", media: media() };
                            }
                        }
                    />
                    {#if block.accessory.kind === "thumbnail"}
                        <MediaField
                            bind:url={block.accessory.media.url}
                            bind:description={block.accessory.media.description}
                            bind:spoiler={block.accessory.media.spoiler}
                        />
                    {:else}
                        <ButtonField button={block.accessory} />
                    {/if}
                </div>
            {:else if block.kind === "gallery"}
                <ol class="flex flex-col gap-2" {@attach sortable({ onmove: reorder(block.items) })}>
                    {#each block.items as item, at (item.id)}
                        <li data-sortable-index={at} class={["flex items-start gap-1", sortableItem]}>
                            {#if block.items.length > 1}<span class="pt-1">{@render dragHandle("Drag to reorder")}</span>{/if}
                            <div class="min-w-0 flex-1">
                                <MediaField bind:url={item.url} bind:description={item.description} bind:spoiler={item.spoiler} />
                            </div>
                            {#if block.items.length > 1}
                                <span class="pt-1">{@render remove("Remove item", () => block.kind === "gallery" && block.items.splice(at, 1))}</span>
                            {/if}
                        </li>
                    {/each}
                </ol>
                {#if block.items.length < LIMITS.galleryItems}
                    <div class="flex flex-wrap gap-2">
                        <Tooltip content={composer.mediaRoom < 1 ? NO_ROOM.media : null}>
                            <Button size="sm" disabled={composer.mediaRoom < 1} onclick={() => block.kind === "gallery" && block.items.push(media())}>
                                <MaterialSymbolsAddRounded />Add item
                            </Button>
                        </Tooltip>
                        <Tooltip content={composer.mediaRoom < 1 && block.items.every((item) => item.url) ? NO_ROOM.media : null}>
                            <Button size="sm" disabled={composer.mediaRoom < 1 && block.items.every((item) => item.url)} onclick={uploadMany}>
                                <MaterialSymbolsUploadRounded />Upload several
                            </Button>
                        </Tooltip>
                    </div>
                {/if}
            {:else if block.kind === "file"}
                <MediaField files bind:url={block.url} bind:spoiler={block.spoiler} />
            {:else if block.kind === "separator"}
                <div class="flex flex-wrap items-center gap-2">
                    <OptionChip icon={MaterialSymbolsHorizontalRuleRounded} bind:pressed={block.divider}>Line</OptionChip>
                    <Segmented
                        label="Gap"
                        options={[
                            { value: "small", label: "Small gap" },
                            { value: "large", label: "Large gap" },
                        ]}
                        bind:value={
                            () => (block.kind === "separator" && block.large ? "large" : "small"),
                            (value) => block.kind === "separator" && (block.large = value === "large")
                        }
                    />
                </div>
            {:else if block.kind === "row"}
                <ol class="flex flex-col gap-4" {@attach sortable({ onmove: reorder(block.buttons) })}>
                    {#each block.buttons as button, at (button.id)}
                        <li data-sortable-index={at} class={["flex items-start gap-1", sortableItem]}>
                            {#if block.buttons.length > 1}<span class="pt-1">{@render dragHandle("Drag to reorder")}</span>{/if}
                            <div class="min-w-0 flex-1"><ButtonField {button} /></div>
                            {#if block.buttons.length > 1}
                                <span class="pt-1">{@render remove("Remove button", () => block.kind === "row" && block.buttons.splice(at, 1))}</span>
                            {/if}
                        </li>
                    {/each}
                </ol>
                {#if block.buttons.length < LIMITS.rowButtons}
                    <Tooltip content={composer.room < 1 ? NO_ROOM.components : null} class="w-fit">
                        <Button size="sm" disabled={composer.room < 1} onclick={() => block.kind === "row" && block.buttons.push(linkButton())}>
                            <MaterialSymbolsAddRounded />Add button
                        </Button>
                    </Tooltip>
                {/if}
            {/if}
        </div>
    {/if}
</li>
