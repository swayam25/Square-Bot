<script lang="ts">
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Picture from "#lib/components/ui/Picture.svelte";
    import { focusRing } from "#lib/components/ui/styles.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { IMAGE_MAX_BYTES, IMAGE_TYPES } from "#lib/profile.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { FileUpload, useFileUpload } from "@ark-ui/svelte/file-upload";
    import MaterialSymbolsDeleteRounded from "~icons/material-symbols/delete-rounded";
    import MaterialSymbolsUploadRounded from "~icons/material-symbols/upload-rounded";

    let {
        kind,
        name,
        value = $bindable(),
        fallback,
        color,
    }: {
        kind: "avatar" | "banner";
        name: string;
        value: string | null;
        fallback: string | null;
        color?: string | null;
    } = $props();

    const shown = $derived(value ?? fallback);

    function read(file: File) {
        const reader = new FileReader();
        reader.onload = () => (value = reader.result as string);
        reader.onerror = () => toast.error("Square couldn't read that file", { description: "Try picking it again." });
        reader.readAsDataURL(file);
    }

    const uid = $props.id();
    const upload = useFileUpload(() => ({
        id: `image-${uid}`,
        accept: IMAGE_TYPES,
        maxFiles: 1,
        maxFileSize: IMAGE_MAX_BYTES,
        onFileAccept: ({ files }) => {
            if (files[0]) read(files[0]);
            upload().clearFiles();
        },
        onFileReject: ({ files }) => {
            const tooBig = files[0]?.errors.includes("FILE_TOO_LARGE");
            toast.error(`Square can't use that ${kind}`, {
                description: tooBig ? `Pick an image up to ${IMAGE_MAX_BYTES / 1024 / 1024} MB.` : "Pick a PNG, JPEG or GIF.",
            });
            upload().clearFiles();
        },
    }));
</script>

<FileUpload.RootProvider value={upload} class={["relative flex", kind === "avatar" ? "w-fit" : "w-full"]}>
    <Tooltip content="Drop or pick a new {kind}" class={kind === "banner" ? "w-full" : undefined}>
        <FileUpload.Dropzone
            class={[
                "group relative flex shrink-0 cursor-pointer overflow-hidden bg-gray-800",
                focusRing,
                kind === "avatar" ? "size-20 rounded-full" : "aspect-5/2 w-full rounded-2xl",
            ]}
        >
            {#if kind === "avatar"}
                <Avatar src={shown} {name} class="size-full" />
            {:else if shown}
                <Picture src={shown} alt="" class="size-full">
                    {#snippet fallback({ loading })}<span class={["size-full", loading && "skeleton"]}></span>{/snippet}
                </Picture>
            {:else}
                <span class="size-full" style:background-color={color ?? undefined}></span>
            {/if}
            <span
                aria-hidden="true"
                class="absolute inset-0 flex items-center justify-center rounded-[inherit] bg-gray-950/60 opacity-0 backdrop-blur-sm transition-opacity duration-200 group-hover:opacity-100 group-data-dragging:opacity-100"
            >
                <MaterialSymbolsUploadRounded class="size-6" />
            </span>
        </FileUpload.Dropzone>
    </Tooltip>
    {#if value}
        <Tooltip content="Remove {kind}" class={["absolute", kind === "avatar" ? "-top-1 -right-1" : "top-2 right-2"]}>
            <Button size="xs" icon class="shadow-lg shadow-black/40" onclick={() => (value = null)}><MaterialSymbolsDeleteRounded /></Button>
        </Tooltip>
    {/if}
    <FileUpload.HiddenInput />
</FileUpload.RootProvider>
