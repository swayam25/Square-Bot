<script lang="ts">
    import Button from "#lib/components/ui/Button.svelte";
    import { errorMessage } from "#lib/errors.ts";
    import { toast } from "#lib/toast.svelte.ts";
    import { beforeNavigate } from "$app/navigation";
    import { cubicIn, cubicOut } from "svelte/easing";
    import { fade, slide } from "svelte/transition";

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

    let bar = $state<HTMLElement>();

    // The control just changed is often low on a short window, right where the bar lands. Scroll it clear while the bar fades in
    function reveal() {
        let target = document.activeElement;
        if (!bar || !(target instanceof HTMLElement) || target === document.body || bar.contains(target)) return;
        // Ark's toggles and checkboxes keep focus on a 1px hidden input that isn't where the control is drawn
        if (target.getBoundingClientRect().height <= 1) target = target.closest<HTMLElement>("[data-part=root]") ?? target;
        const covered = target.getBoundingClientRect().bottom + 16 - bar.getBoundingClientRect().top;
        if (covered <= 0) return;
        let scroller = target.parentElement;
        while (scroller && !/(auto|scroll)/.test(getComputedStyle(scroller).overflowY)) scroller = scroller.parentElement;
        (scroller ?? window).scrollBy({ top: covered, behavior: "smooth" });
    }

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
    <!-- Room for the bar. It's there at once, so the reveal scroll isn't clamped, and shrinks on the way out so the page glides back -->
    <div aria-hidden="true" class="h-40 md:h-24" out:slide={{ duration: 150, easing: cubicIn }}></div>
    <div
        class="pointer-events-none fixed inset-x-4 bottom-[calc(5.5rem+env(safe-area-inset-bottom))] z-40 flex justify-center md:right-[calc(var(--details)+3rem)] md:bottom-8 md:left-[calc(var(--sidebar)+3rem)]"
        in:fade={{ duration: 200, easing: cubicOut }}
        out:fade={{ duration: 150, easing: cubicIn }}
        onintrostart={reveal}
    >
        {#key nudges}
            <div
                bind:this={bar}
                role="region"
                aria-label="Unsaved changes"
                class={[
                    "pointer-events-auto flex w-full max-w-2xl flex-col gap-4 rounded-3xl bg-gray-800 p-4 shadow-2xl shadow-black/50 md:flex-row md:items-center md:rounded-full md:py-2 md:pr-2 md:pl-6",
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
