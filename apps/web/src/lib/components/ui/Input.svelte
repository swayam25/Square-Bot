<script lang="ts">
    import FieldError from "#lib/components/ui/FieldError.svelte";
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
        // Turns the field red and explains why while it is hovered or focused
        error?: string | null;
        ref?: HTMLInputElement | null;
        class?: ClassValue;
    };

    let { value = $bindable(), ref = $bindable(null), type = "text", icon: Icon, error, class: className, ...rest }: Props = $props();

    const errorId = $props.id();

    const iconButton =
        "flex size-8 shrink-0 items-center justify-center rounded-xl text-gray-400 hover:bg-white/10 hover:text-gray-100 disabled:opacity-50 md:size-6 md:rounded-lg [&_svg]:size-4";

    function step(direction: 1 | -1) {
        if (!ref) return;
        if (direction === 1) ref.stepUp();
        else ref.stepDown();
        ref.dispatchEvent(new Event("input", { bubbles: true }));
        ref.dispatchEvent(new Event("change", { bubbles: true }));
    }
</script>

<label class={[field, "group/field relative", (type === "number" || type === "search") && "pr-2", className]}>
    {#if Icon}<Icon class="size-5 shrink-0 text-gray-400" />{/if}
    <input
        bind:this={ref}
        bind:value
        {type}
        aria-invalid={!!error || undefined}
        aria-describedby={error ? errorId : undefined}
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
    <FieldError id={errorId} {error} />
</label>
