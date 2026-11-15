<script lang="ts">
    import EmojiPicker from "#lib/components/EmojiPicker.svelte";
    import { fieldText } from "#lib/components/ui/styles.ts";
    import type { ClassValue, HTMLTextareaAttributes } from "svelte/elements";

    type Props = Omit<HTMLTextareaAttributes, "class"> & {
        invalid?: boolean;
        emojis?: { id: string; name: string; iconUrl: string | null };
        class?: ClassValue;
    };

    let { value = $bindable(), invalid = false, emojis, maxlength, class: className, ...rest }: Props = $props();

    let area = $state<HTMLTextAreaElement | null>(null);
    const length = $derived(typeof value === "string" ? value.length : 0);

    function insert(text: string) {
        if (!area) return;
        const { selectionStart: start, selectionEnd: end } = area;
        if (maxlength != null && area.value.length - (end - start) + text.length > maxlength) return;
        area.setRangeText(text, start, end, "end");
        area.dispatchEvent(new Event("input", { bubbles: true }));
    }
</script>

<div
    class={[
        "flex w-full min-w-0 flex-col rounded-3xl bg-gray-800 text-sm",
        "ring-0 ring-accent/60 transition-[background-color,box-shadow] duration-200 ease-out ring-inset",
        "focus-within:ring-2 hover:bg-gray-700",
        "has-aria-invalid:bg-red-400/10 has-aria-invalid:ring-red-400/40",
        "has-[textarea:disabled]:pointer-events-none has-[textarea:disabled]:opacity-50",
        className,
    ]}
>
    <textarea
        bind:this={area}
        bind:value
        {maxlength}
        aria-invalid={invalid || undefined}
        class={[fieldText, "field-sizing-content min-h-24 resize-none px-4 pt-3", !(emojis || maxlength) && "pb-3"]}
        {...rest}></textarea>
    {#if emojis || maxlength}
        <div class="flex items-center gap-2 px-4 pt-2 pb-3">
            {#if emojis}
                <EmojiPicker
                    guild={emojis}
                    placement="top-start"
                    disabled={!!rest.disabled}
                    triggerClass="-ml-2"
                    onpick={insert}
                    finalFocus={() => area}
                />
            {/if}
            {#if maxlength}
                <span aria-hidden="true" class="ml-auto font-mono text-xs text-gray-400">{length}/{maxlength}</span>
            {/if}
        </div>
    {/if}
</div>
