<script module lang="ts">
    export const field = [
        "flex h-12 w-full min-w-0 items-center gap-2 rounded-full bg-surface-2 px-4 text-sm md:h-10",
        "ring-0 ring-accent/40 transition-[background-color,box-shadow] duration-200 ease-out",
        "hover:bg-surface-3 focus-within:ring-4",
        "has-[[aria-invalid=true]]:bg-red-400/10 has-[[aria-invalid=true]]:ring-red-400/40",
        "has-[input:disabled]:pointer-events-none has-[input:disabled]:opacity-50",
    ];

    export const fieldText = "w-full min-w-0 flex-1 bg-transparent outline-none placeholder:text-mist-400";
</script>

<script lang="ts">
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
        "flex size-8 shrink-0 items-center justify-center rounded-full text-mist-400 hover:bg-white/10 hover:text-mist-100 disabled:opacity-50 md:size-6 [&_svg]:size-4";

    function step(direction: 1 | -1) {
        if (!ref) return;
        if (direction === 1) ref.stepUp();
        else ref.stepDown();
        ref.dispatchEvent(new Event("input", { bubbles: true }));
        ref.dispatchEvent(new Event("change", { bubbles: true }));
    }
</script>

<label class={[field, (type === "number" || type === "search") && "pr-2", className]}>
    {#if Icon}<Icon class="size-5 shrink-0 text-mist-400" />{/if}
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
        <button
            type="button"
            tabindex="-1"
            onpointerdown={(event) => event.preventDefault()}
            aria-label="Clear"
            class={iconButton}
            onclick={() => ((value = ""), ref?.focus())}
        >
            <MaterialSymbolsCloseRounded />
        </button>
    {:else if type === "number"}
        <button
            type="button"
            tabindex="-1"
            onpointerdown={(event) => event.preventDefault()}
            aria-label="Decrease"
            class={iconButton}
            disabled={rest.disabled}
            onclick={() => step(-1)}
        >
            <MaterialSymbolsRemoveRounded />
        </button>
        <button
            type="button"
            tabindex="-1"
            onpointerdown={(event) => event.preventDefault()}
            aria-label="Increase"
            class={iconButton}
            disabled={rest.disabled}
            onclick={() => step(1)}
        >
            <MaterialSymbolsAddRounded />
        </button>
    {/if}
</label>
