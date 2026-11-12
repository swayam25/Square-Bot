<script lang="ts">
    import Button from "#lib/components/ui/Button.svelte";
    import { errorMessage } from "#lib/errors.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { beforeNavigate } from "$app/navigation";
    import { cubicOut } from "svelte/easing";
    import { fly } from "svelte/transition";

    let {
        dirty,
        invalid = "",
        onsave,
        ondiscard,
    }: { dirty: boolean; invalid?: string; onsave: () => Promise<unknown>; ondiscard: () => void } = $props();

    let saving = $state(false);
    let problem = $state("");
    let nudges = $state(0);

    $effect(() => {
        if (!dirty) {
            problem = "";
            nudges = 0;
        }
    });

    beforeNavigate((navigation) => {
        if (!dirty || saving) return;
        navigation.cancel();
        if (!navigation.willUnload) nudges++;
    });

    async function save() {
        saving = true;
        problem = "";
        try {
            await onsave();
            toast.success("Changes saved");
        } catch (err) {
            problem = errorMessage(err, "Square couldn't save that. Try again.");
        } finally {
            saving = false;
        }
    }
</script>

{#if dirty}
    <div aria-hidden="true" class="h-40 md:h-24"></div>
    <div
        class="pointer-events-none fixed inset-x-4 bottom-[calc(5.5rem+env(safe-area-inset-bottom))] z-40 flex justify-center md:right-[calc(var(--details)+3rem)] md:bottom-8 md:left-[calc(var(--sidebar)+3rem)]"
        transition:fly={{ y: 24, duration: 300, easing: cubicOut }}
    >
        {#key nudges}
            <div
                role="region"
                aria-label="Unsaved changes"
                class={[
                    "pointer-events-auto flex w-full max-w-2xl flex-col gap-4 rounded-3xl bg-surface-2 p-4 shadow-2xl shadow-black/50 md:flex-row md:items-center md:rounded-full md:py-2 md:pr-2 md:pl-6",
                    nudges > 0 && "animate-nudge",
                ]}
            >
                <p
                    aria-live="polite"
                    class={["min-w-0 flex-1 text-sm font-medium", problem || invalid ? "text-red-400" : nudges > 0 && "text-amber-400"]}
                >
                    {problem || invalid || (nudges > 0 ? "Save or discard your changes first." : "You have unsaved changes.")}
                </p>
                <div class="flex gap-2 *:flex-1 md:*:flex-none">
                    <Button variant="ghost" disabled={saving} onclick={ondiscard}>Discard</Button>
                    <Button variant="primary" loading={saving} disabled={!!invalid} onclick={save}>{saving ? "Saving…" : "Save changes"}</Button>
                </div>
            </div>
        {/key}
    </div>
{/if}
