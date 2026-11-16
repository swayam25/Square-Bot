<script lang="ts" generics="T">
    import Button from "#lib/components/ui/Button.svelte";
    import Dialog from "#lib/components/ui/Dialog.svelte";
    import { errorMessage } from "#lib/errors.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { settled } from "svelte";

    let {
        open = $bindable(false),
        title,
        description,
        label,
        busy = "Working…",
        done,
        run,
        apply,
    }: {
        open?: boolean;
        title: string;
        description: string;
        label: string;
        busy?: string;
        done: string;
        run: () => Promise<T>;
        apply?: (result: T) => void;
    } = $props();

    let working = $state(false);
    let problem = $state("");

    $effect(() => {
        if (open) problem = "";
    });

    async function confirm() {
        working = true;
        problem = "";
        try {
            const result = await run();
            open = false;
            working = false;
            // Updating a query while an Ark dialog is open froze the page for seconds, so the result lands after it closes
            await settled();
            toast.success(done);
            apply?.(result);
        } catch (err) {
            problem = errorMessage(err, "Square couldn't do that. Try again.");
        } finally {
            working = false;
        }
    }
</script>

<Dialog bind:open={() => open, (next) => !working && (open = next)} {title} dismissable={!working}>
    <div class="flex flex-col gap-4 text-sm">
        <p class="text-gray-400">{description}</p>
        {#if problem}<p class="font-medium text-red-400">{problem}</p>{/if}
    </div>
    {#snippet footer()}
        <Button variant="ghost" disabled={working} onclick={() => (open = false)}>Cancel</Button>
        <Button variant="danger" loading={working} onclick={confirm}>{working ? busy : label}</Button>
    {/snippet}
</Dialog>
