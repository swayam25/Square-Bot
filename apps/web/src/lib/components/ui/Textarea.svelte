<script lang="ts">
    import { fieldText } from "#lib/components/ui/styles.ts";
    import type { ClassValue, HTMLTextareaAttributes } from "svelte/elements";

    type Props = Omit<HTMLTextareaAttributes, "class"> & { invalid?: boolean; class?: ClassValue };

    let { value = $bindable(), invalid = false, maxlength, class: className, ...rest }: Props = $props();

    const length = $derived(typeof value === "string" ? value.length : 0);
</script>

<label
    class={[
        "flex w-full min-w-0 flex-col gap-2 rounded-3xl bg-gray-800 px-4 py-3 text-sm",
        "ring-0 ring-accent/60 transition-[background-color,box-shadow] duration-200 ease-out ring-inset",
        "focus-within:ring-2 hover:bg-gray-700",
        "has-aria-invalid:bg-red-400/10 has-aria-invalid:ring-red-400/40",
        "has-[textarea:disabled]:pointer-events-none has-[textarea:disabled]:opacity-50",
        className,
    ]}
>
    <textarea bind:value {maxlength} aria-invalid={invalid || undefined} class={[fieldText, "field-sizing-content min-h-24 resize-none"]} {...rest}
    ></textarea>
    {#if maxlength}
        <span aria-hidden="true" class="self-end font-mono text-xs text-gray-400">{length}/{maxlength}</span>
    {/if}
</label>
