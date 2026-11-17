<script module lang="ts">
    import { customUrl } from "#lib/emoji/emoji.ts";

    function custom(text: string | null) {
        const match = /^<(a?):(\w+):(\d{17,20})>$/.exec(text ?? "");
        return match ? { id: match[3]!, name: match[2]!, animated: match[1] === "a" } : null;
    }
</script>

<script lang="ts">
    import EmojiPicker from "#lib/components/fields/EmojiPicker.svelte";
    import FieldError from "#lib/components/ui/FieldError.svelte";
    import { focusRing } from "#lib/components/ui/styles.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";

    let {
        values = $bindable([]),
        max,
        guild,
        error = null,
    }: {
        values?: string[];
        max: number;
        guild: { id: string; name: string; iconUrl: string | null };
        error?: string | null;
    } = $props();

    const errorId = $props.id();
    const tile = "flex size-12 shrink-0 items-center justify-center rounded-control-lg bg-gray-800 md:size-10 md:rounded-2xl";
</script>

<div class="group/field relative flex flex-wrap items-center gap-2" role="group" aria-describedby={error ? errorId : undefined}>
    {#each values as value, index (value)}
        {@const found = custom(value)}
        <Tooltip content="Remove">
            <button
                type="button"
                class={[tile, "cursor-pointer hover:bg-gray-700", error && "bg-red-400/10 outline-2 outline-red-400", focusRing]}
                onclick={() => values.splice(index, 1)}
            >
                {#if found}
                    <img src={customUrl(found)} alt=":{found.name}:" class="size-6 object-contain" />
                {:else}
                    <span class="font-emoji text-2xl/none">{value}</span>
                {/if}
            </button>
        </Tooltip>
    {/each}
    {#if values.length < max}
        <EmojiPicker
            {guild}
            placement="bottom-start"
            triggerClass={[tile, "md:size-10! md:rounded-2xl!", error && !values.length && "bg-red-400/10! text-red-400!"]}
            onpick={(text) => !values.includes(text) && values.push(text)}
        />
    {/if}
    <FieldError id={errorId} {error} />
</div>
