<script lang="ts" generics="T">
    import Button from "#lib/components/ui/Button.svelte";
    import Dialog from "#lib/components/ui/Dialog.svelte";
    import Input from "#lib/components/ui/Input.svelte";
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
        variant = "danger",
        confirmText,
        run,
        apply,
    }: {
        open?: boolean;
        title: string;
        description: string;
        label: string;
        busy?: string;
        done: string;
        variant?: "primary" | "danger";
        confirmText?: string;
        run: () => Promise<T>;
        apply?: (result: T) => void;
    } = $props();

    let working = $state(false);
    let typed = $state("");
    const unlocked = $derived(!confirmText || typed.trim() === confirmText.trim());

    $effect(() => {
        if (!open) return;
        typed = "";
    });

    async function confirm() {
        working = true;
        try {
            const result = await run();
            open = false;
            working = false;
            // Updating a query while an Ark dialog is open froze the page for seconds, so the result lands after it closes
            await settled();
            toast.success(done);
            apply?.(result);
        } catch (err) {
            toast.error(errorMessage(err, "Square couldn't do that. Try again."));
        } finally {
            working = false;
        }
    }
</script>

<Dialog bind:open={() => open, (next) => !working && (open = next)} {title} dismissable={!working}>
    <div class="flex flex-col gap-4 text-sm">
        <p class="text-gray-400">{description}</p>
        {#if confirmText}
            <label class="flex flex-col gap-2">
                <span>Type <strong class="font-semibold text-gray-100">{confirmText}</strong> to confirm</span>
                <Input aria-label="Type {confirmText} to confirm" autocomplete="off" spellcheck="false" disabled={working} bind:value={typed} />
            </label>
        {/if}
    </div>
    {#snippet footer()}
        <Button variant="ghost" disabled={working} onclick={() => (open = false)}>Cancel</Button>
        <Button {variant} loading={working} disabled={!unlocked} onclick={confirm}>{working ? busy : label}</Button>
    {/snippet}
</Dialog>
