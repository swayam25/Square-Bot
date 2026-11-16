<script lang="ts">
    import Popup from "#lib/components/ui/Popup.svelte";
    import { focusRing } from "#lib/components/ui/styles.ts";
    import { create, getComposer, LABELS, type Kind } from "#lib/composer.svelte.ts";
    import { mobile } from "#lib/media.ts";
    import MaterialSymbolsAddRounded from "~icons/material-symbols/add-rounded";
    import { KINDS } from "./kinds.ts";

    let { kinds, label = "Add component", onadd }: { kinds: Kind[]; label?: string; onadd: (kind: Kind) => void } = $props();

    const composer = getComposer();
    let open = $state(false);

    function add(kind: Kind) {
        open = false;
        onadd(kind);
    }
</script>

<Popup
    bind:open
    title={label}
    placement="bottom-start"
    contentClass="w-80"
    triggerClass={[
        "ripple inline-flex h-12 w-fit shrink-0 items-center gap-2 rounded-full bg-gray-800 px-6 text-sm font-medium hover:bg-gray-700 md:h-10 md:px-4",
        focusRing,
    ]}
>
    {#snippet trigger()}<MaterialSymbolsAddRounded class="size-4" />{label}{/snippet}
    <div class={["flex flex-col gap-1", mobile.current && "px-4 pb-4"]}>
        {#each kinds as kind (kind)}
            {@const { icon: Icon, hint } = KINDS[kind]}
            {@const full = composer.full(create(kind, composer.mediaRoom > 0))}
            <button
                type="button"
                disabled={!!full}
                class={[
                    "ripple flex w-full items-center gap-4 rounded-xl px-4 py-2 text-left hover:bg-white/10 disabled:pointer-events-none disabled:opacity-50",
                    mobile.current && "min-h-12 rounded-2xl",
                ]}
                onclick={() => add(kind)}
            >
                <Icon class="size-5 shrink-0 text-accent" />
                <span class="flex min-w-0 flex-col">
                    <span class="text-sm font-medium">{LABELS[kind]}</span>
                    <span class="text-xs text-gray-400">{full ?? hint}</span>
                </span>
            </button>
        {/each}
    </div>
</Popup>
