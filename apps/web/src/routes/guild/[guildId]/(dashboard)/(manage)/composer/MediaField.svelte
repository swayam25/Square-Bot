<script lang="ts">
    import Button from "#lib/components/ui/Button.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import { field } from "#lib/components/ui/styles.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { accepts, ATTACHMENT, getComposer, isVideo, LIMITS, MEDIA_TYPES, pickFiles, validUrl } from "#lib/composer.svelte.ts";
    import { bytes } from "#lib/format.ts";
    import { imageLoad } from "#lib/image-load.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import MaterialSymbolsAttachFileRounded from "~icons/material-symbols/attach-file-rounded";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";
    import MaterialSymbolsImageRounded from "~icons/material-symbols/image-rounded";
    import MaterialSymbolsUploadRounded from "~icons/material-symbols/upload-rounded";
    import MaterialSymbolsVisibilityOffRounded from "~icons/material-symbols/visibility-off-rounded";
    import OptionChip from "./OptionChip.svelte";

    let {
        url = $bindable(),
        description = $bindable(),
        spoiler = $bindable(false),
        files = false,
    }: {
        url: string;
        // Left out where Discord has no alt text, like File components
        description?: string;
        spoiler?: boolean;
        // Any file, uploaded only. Otherwise pictures and videos, from a link or an upload
        files?: boolean;
    } = $props();

    const composer = getComposer();
    const accept = $derived(files ? undefined : MEDIA_TYPES);
    const upload = $derived(composer.uploads.of(url));
    const lost = $derived(url.startsWith(ATTACHMENT) && !upload);
    const preview = $derived(upload?.url ?? (validUrl(url) ? url.trim() : null));
    const video = $derived(upload ? isVideo(upload.name, upload.file.type) : isVideo(url));
    let dragging = $state(false);
    // Resets whenever the preview changes
    let broken = $derived.by(() => (void preview, false));

    function take(file: File | undefined) {
        if (!file) return;
        if (!accepts(file, accept)) {
            toast.error("Discord can't show that here", { description: "Pick a picture (PNG, JPEG, GIF, WebP) or a video (MP4, WebM, MOV)." });
            return;
        }
        const link = composer.upload(file);
        if (link) url = link;
    }

    async function choose() {
        take((await pickFiles(accept))[0]);
    }

    function drop(event: DragEvent) {
        event.preventDefault();
        dragging = false;
        take(event.dataTransfer?.files[0]);
    }
</script>

<div
    role="group"
    aria-label={files ? "File" : "Picture or video"}
    class={["flex flex-col gap-2 rounded-3xl transition-colors", dragging && "bg-accent/10"]}
    ondragover={(event) => {
        if (!event.dataTransfer?.types.includes("Files")) return;
        event.preventDefault();
        dragging = true;
    }}
    ondragleave={(event) => {
        if (!(event.currentTarget as HTMLElement).contains(event.relatedTarget as Node | null)) dragging = false;
    }}
    ondrop={drop}
>
    <div class="flex items-center gap-2">
        {#if !files}
            <span class="flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-gray-800 text-gray-400 md:size-10">
                {#if preview && !broken && video}
                    <video src={preview} muted preload="metadata" class="size-full object-cover"></video>
                {:else if preview && !broken}
                    <img src={preview} alt="" class="size-full object-cover" {@attach imageLoad(undefined, () => (broken = true))} />
                {:else}
                    <MaterialSymbolsImageRounded class="size-5" />
                {/if}
            </span>
        {/if}
        {#if upload || lost}
            <span class={[field, "pointer-events-none font-medium", lost && "bg-red-400/10 text-red-400"]}>
                <MaterialSymbolsAttachFileRounded />
                <span class="truncate">{lost ? `${url.slice(ATTACHMENT.length)} is gone, upload it again` : upload!.name}</span>
                {#if upload}<span class="ml-auto shrink-0 font-mono text-xs text-gray-400">{bytes(upload.file.size)}</span>{/if}
            </span>
            <Tooltip content="Remove">
                <Button icon variant="ghost" onclick={() => (url = "")}><MaterialSymbolsCloseRounded /></Button>
            </Tooltip>
        {:else if files}
            <span class={[field, "pointer-events-none text-gray-400"]}>
                <MaterialSymbolsAttachFileRounded />
                <span class="truncate">Drop a file here or upload one</span>
            </span>
        {:else}
            <Input
                type="url"
                aria-label="Picture or video link"
                placeholder="https:// link, or drop a file"
                maxlength={2048}
                error={url.trim() && !validUrl(url) ? "Use a full link starting with https://" : null}
                bind:value={url}
            />
        {/if}
        <Tooltip content="Upload {files ? 'a file' : 'a picture or video'}">
            <Button icon onclick={choose}><MaterialSymbolsUploadRounded /></Button>
        </Tooltip>
    </div>
    <div class="flex items-center gap-2">
        {#if description !== undefined}
            <Input aria-label="Alt text" placeholder="Alt text (optional)" maxlength={LIMITS.description} bind:value={description} />
        {/if}
        <OptionChip icon={MaterialSymbolsVisibilityOffRounded} bind:pressed={spoiler}>Spoiler</OptionChip>
    </div>
</div>
