<script lang="ts">
    let { label, value, size = "md", accent = false }: { label: string; value: string; size?: "md" | "lg"; accent?: boolean } = $props();
</script>

<div class={["flex min-h-12 flex-col justify-center gap-0.5 rounded-2xl bg-gray-800", size === "lg" ? "p-4" : "px-4 py-2"]}>
    <span class="text-xs text-gray-400">{label}</span>
    <span class={["truncate", size === "lg" ? "font-display text-xl font-semibold" : "text-sm font-medium", accent && "text-accent"]}>{value}</span>
</div>
