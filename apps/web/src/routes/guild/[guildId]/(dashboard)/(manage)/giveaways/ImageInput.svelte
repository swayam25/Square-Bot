<script lang="ts">
    import Button from "#lib/components/ui/Button.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import Picture from "#lib/components/ui/Picture.svelte";
    import { field, focusRing } from "#lib/components/ui/styles.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { toast } from "#lib/toast.svelte.ts";
    import { FileUpload, useFileUpload } from "@ark-ui/svelte/file-upload";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";
    import MaterialSymbolsImageRounded from "~icons/material-symbols/image-rounded";
    import MaterialSymbolsUploadRounded from "~icons/material-symbols/upload-rounded";
    import { IMAGE_MAX_BYTES, IMAGE_TYPES, type Draft } from "./giveaway.ts";

    let { draft = $bindable(), stored, error }: { draft: Draft; stored: string | null; error: string | null } = $props();

    const shown = $derived(draft.imageUpload?.dataUrl ?? (draft.imageFile ? stored : null));
    const name = $derived(draft.imageUpload?.name ?? (draft.imageFile ? "Uploaded image" : null));

    function read(file: File) {
        const reader = new FileReader();
        reader.onload = () => (draft.imageUpload = { name: file.name, dataUrl: reader.result as string });
        reader.onerror = () => toast.error("Square couldn't read that file", { description: "Try picking it again." });
        reader.readAsDataURL(file);
    }

    function remove() {
        draft.imageUpload = null;
        draft.imageFile = null;
    }

    const uid = $props.id();
    const upload = useFileUpload(() => ({
        id: `giveaway-image-${uid}`,
        accept: IMAGE_TYPES,
        maxFiles: 1,
        maxFileSize: IMAGE_MAX_BYTES,
        onFileAccept: ({ files }) => {
            if (files[0]) read(files[0]);
            upload().clearFiles();
        },
        onFileReject: ({ files }) => {
            const tooBig = files[0]?.errors.includes("FILE_TOO_LARGE");
            toast.error("Square can't use that image", {
                description: tooBig ? `Pick an image up to ${IMAGE_MAX_BYTES / 1024 / 1024} MB.` : "Pick a PNG, JPEG, GIF or WebP.",
            });
            upload().clearFiles();
        },
    }));
</script>

<FileUpload.RootProvider value={upload} class="flex min-w-0 items-center gap-2">
    {#if name}
        <div class={[field, "pl-1"]}>
            <span class="size-10 shrink-0 overflow-hidden rounded-full bg-gray-700 md:size-8">
                {#if shown}
                    <Picture src={shown} alt="" class="size-full object-cover">
                        {#snippet fallback({ loading })}<span class={["size-full", loading && "skeleton"]}></span>{/snippet}
                    </Picture>
                {:else}
                    <span class="flex size-full items-center justify-center text-gray-400"><MaterialSymbolsImageRounded class="size-4" /></span>
                {/if}
            </span>
            <span class="min-w-0 flex-1 truncate">{name}</span>
            <Tooltip content="Remove image">
                <Button variant="ghost" size="xs" icon onclick={remove}><MaterialSymbolsCloseRounded /></Button>
            </Tooltip>
        </div>
    {:else}
        <Input type="url" aria-label="Image link" placeholder="https://" {error} bind:value={draft.imageUrl} />
    {/if}
    <Tooltip content={name ? "Upload another image" : "Upload an image"}>
        <FileUpload.Trigger
            class={[
                "ripple flex size-12 shrink-0 cursor-pointer items-center justify-center rounded-full bg-gray-800 hover:bg-gray-700 md:size-10 [&>svg]:size-5",
                focusRing,
            ]}
        >
            <MaterialSymbolsUploadRounded />
        </FileUpload.Trigger>
    </Tooltip>
    <FileUpload.HiddenInput />
</FileUpload.RootProvider>
