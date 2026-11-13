<script lang="ts">
    import { Checkbox } from "@ark-ui/svelte/checkbox";
    import MaterialSymbolsCheckRounded from "~icons/material-symbols/check-rounded";

    let { checked = $bindable(false), label, disabled = false }: { checked?: boolean; label: string; disabled?: boolean } = $props();
</script>

<Checkbox.Root
    {checked}
    {disabled}
    onCheckedChange={(details) => (checked = details.checked === true)}
    class="group relative inline-flex shrink-0 cursor-pointer items-center data-disabled:cursor-default data-disabled:opacity-50"
>
    <Checkbox.Control
        aria-label={label}
        class="flex size-6 items-center justify-center rounded-lg bg-black/40 transition-colors duration-300 group-focus-visible:outline-2 group-focus-visible:outline-offset-2 group-focus-visible:outline-accent data-[state=checked]:bg-accent data-[state=checked]:text-cyan-950"
    >
        <MaterialSymbolsCheckRounded
            aria-hidden="true"
            class="size-5 scale-50 opacity-0 transition-[opacity,scale] duration-150 ease-in group-data-[state=checked]:scale-100 group-data-[state=checked]:opacity-100 group-data-[state=checked]:duration-400 group-data-[state=checked]:ease-spring motion-reduce:transition-none"
        />
    </Checkbox.Control>
    <Checkbox.HiddenInput />
</Checkbox.Root>
