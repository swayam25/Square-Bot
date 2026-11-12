<script lang="ts" generics="T">
    import Button from "#lib/components/ui/Button.svelte";
    import Dialog from "#lib/components/ui/Dialog.svelte";
    import { errorMessage } from "#lib/errors.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { settled, type Component } from "svelte";
    import MaterialSymbolsRestartAltRounded from "~icons/material-symbols/restart-alt-rounded";

    let {
        title,
        description,
        label = "Reset",
        done,
        icon: Icon = MaterialSymbolsRestartAltRounded,
        disabled = false,
        reset,
        apply,
    }: {
        title: string;
        description: string;
        label?: string;
        // Shown in the island once it worked
        done: string;
        icon?: Component;
        disabled?: boolean;
        reset: () => Promise<T>;
        apply?: (result: T) => void;
    } = $props();

    let open = $state(false);
    let resetting = $state(false);
    let problem = $state("");

    async function confirm() {
        resetting = true;
        problem = "";
        try {
            const result = await reset();
            open = false;
            resetting = false;
            // Updating a query while an Ark dialog is open froze the page for seconds, so the result lands after it closes
            await settled();
            toast.success(done);
            apply?.(result);
        } catch (err) {
            problem = errorMessage(err, "Square couldn't reset that. Try again.");
        } finally {
            resetting = false;
        }
    }
</script>

<Button {disabled} onclick={() => ((problem = ""), (open = true))}><Icon />{label}</Button>

<Dialog bind:open={() => open, (next) => !resetting && (open = next)} {title} dismissable={!resetting}>
    <div class="flex flex-col gap-4 text-sm">
        <p class="text-mist-400">{description}</p>
        {#if problem}<p class="font-medium text-red-400">{problem}</p>{/if}
    </div>
    {#snippet footer()}
        <Button variant="ghost" disabled={resetting} onclick={() => (open = false)}>Cancel</Button>
        <Button variant="danger" loading={resetting} onclick={confirm}>{resetting ? "Resetting…" : label}</Button>
    {/snippet}
</Dialog>
