<script lang="ts">
    import { field, fieldText } from "#lib/components/ui/styles.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import type { Component } from "svelte";
    import type { ClassValue, HTMLInputAttributes } from "svelte/elements";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import MaterialSymbolsCloseRounded from "~icons/material-symbols/close-rounded";
    import MaterialSymbolsRemoveRounded from "~icons/material-symbols/remove-rounded";

    type Props = Omit<HTMLInputAttributes, "class" | "type"> & {
        type?: "text" | "search" | "number" | "email" | "url";
        icon?: Component;
        invalid?: boolean;
        ref?: HTMLInputElement | null;
        class?: ClassValue;
    };

    let { value = $bindable(), ref = $bindable(null), type = "text", icon: Icon, invalid = false, class: className, ...rest }: Props = $props();

    const iconButton =
        "flex size-8 shrink-0 items-center justify-center rounded-full text-gray-400 hover:bg-white/10 hover:text-gray-100 disabled:opacity-50 md:size-6 [&_svg]:size-4";

    function step(direction: 1 | -1) {
        if (!ref) return;
        if (direction === 1) ref.stepUp();
        else ref.stepDown();
        ref.dispatchEvent(new Event("input", { bubbles: true }));
        ref.dispatchEvent(new Event("change", { bubbles: true }));
    }
</script>

<label class={[field, (type === "number" || type === "search") && "pr-2", className]}>
    {#if Icon}<Icon class="size-4 shrink-0 text-gray-400" />{/if}
    <input
        bind:this={ref}
        bind:value
        {type}
        aria-invalid={invalid || undefined}
        class={[
            fieldText,
            "h-full",
            type === "search" && "[&::-webkit-search-cancel-button]:appearance-none",
            type === "number" &&
                "[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none",
        ]}
        {...rest}
    />
    {#if type === "search" && value}
        <Tooltip content="Clear">
            <button
                type="button"
                tabindex="-1"
                onpointerdown={(event) => event.preventDefault()}
                class={iconButton}
                onclick={() => ((value = ""), ref?.focus())}
            >
                <MaterialSymbolsCloseRounded />
            </button>
        </Tooltip>
    {:else if type === "number"}
        <Tooltip content="Decrease">
            <button
                type="button"
                tabindex="-1"
                onpointerdown={(event) => event.preventDefault()}
                class={iconButton}
                disabled={rest.disabled}
                onclick={() => step(-1)}
            >
                <MaterialSymbolsRemoveRounded />
            </button>
        </Tooltip>
        <Tooltip content="Increase">
            <button
                type="button"
                tabindex="-1"
                onpointerdown={(event) => event.preventDefault()}
                class={iconButton}
                disabled={rest.disabled}
                onclick={() => step(1)}
            >
                <MaterialSymbolsAddRounded />
            </button>
        </Tooltip>
    {/if}
</label>
