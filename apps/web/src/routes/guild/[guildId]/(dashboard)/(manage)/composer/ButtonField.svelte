<script lang="ts">
    import EmojiPicker from "#lib/components/EmojiPicker.svelte";
    import Input from "#lib/components/ui/Input.svelte";
    import { focusRing } from "#lib/components/ui/styles.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { getComposer, LIMITS, parseEmoji, validButtonUrl, type LinkButton } from "#lib/composer.svelte.ts";
    import { customUrl } from "#lib/emoji.ts";
    import MaterialSymbolsBlockRounded from "~icons/material-symbols/block-rounded";
    import MaterialSymbolsLinkRounded from "~icons/material-symbols/link-rounded";
    import OptionChip from "./OptionChip.svelte";

    let { button }: { button: LinkButton } = $props();

    const composer = getComposer();
    const emoji = $derived(button.emoji ? parseEmoji(button.emoji) : null);
    let labelTouched = $state(false);
    let urlTouched = $state(false);

    const labelError = $derived(labelTouched && !button.label.trim() && !button.emoji ? "Add a label or an emoji" : null);
    const urlError = $derived.by(() => {
        if (!button.url.trim()) return urlTouched ? "Buttons need a link, like a server invite" : null;
        return validButtonUrl(button.url) ? null : "Use a full link starting with https://";
    });
</script>

<div class="flex flex-col gap-2">
    <div class="flex items-center gap-2">
        {#if emoji}
            <Tooltip content="Remove emoji">
                <button
                    type="button"
                    class={[
                        "flex size-12 shrink-0 cursor-pointer items-center justify-center rounded-full bg-gray-800 hover:bg-gray-700 md:size-10",
                        focusRing,
                    ]}
                    onclick={() => (button.emoji = "")}
                >
                    {#if emoji.id}
                        <img
                            src={customUrl({ id: emoji.id, animated: emoji.animated ?? false })}
                            alt=":{emoji.name}:"
                            class="size-6 object-contain"
                        />
                    {:else}
                        <span class="font-emoji text-2xl/none">{emoji.name}</span>
                    {/if}
                </button>
            </Tooltip>
        {:else}
            <EmojiPicker guild={composer.guild} placement="bottom-start" onpick={(picked) => (button.emoji = picked)} />
        {/if}
        <Input
            aria-label="Button label"
            placeholder="Label"
            maxlength={LIMITS.label}
            error={labelError}
            onblur={() => (labelTouched = true)}
            bind:value={button.label}
        />
    </div>
    <div class="flex items-center gap-2">
        <Input
            type="url"
            icon={MaterialSymbolsLinkRounded}
            aria-label="Button link"
            placeholder="https://discord.gg/invite"
            maxlength={LIMITS.url}
            error={urlError}
            onblur={() => (urlTouched = true)}
            bind:value={button.url}
        />
        <OptionChip icon={MaterialSymbolsBlockRounded} bind:pressed={button.disabled}>Disabled</OptionChip>
    </div>
</div>
