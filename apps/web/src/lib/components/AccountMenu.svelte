<script lang="ts">
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import { menuRow } from "#lib/components/ui/styles.ts";
    import { ripple } from "#lib/motion.ts";
    import type { Snippet } from "svelte";
    import MaterialSymbolsLogoutRounded from "~icons/material-symbols/logout-rounded";

    let { user, children }: { user: { name: string; username: string; avatarUrl: string | null }; children?: Snippet } = $props();
</script>

<div class="flex items-center gap-4 p-2 pb-4">
    <Avatar src={user.avatarUrl} name={user.name} class="size-12" />
    <div class="flex min-w-0 flex-col">
        <span class="truncate font-semibold">{user.name}</span>
        <span class="truncate font-mono text-sm text-gray-400">@{user.username}</span>
    </div>
</div>
<nav class="flex flex-col gap-1">
    {@render children?.()}
    <form method="POST" action="/logout">
        <button class={[menuRow, "text-red-400 hover:bg-red-400/10 [&>svg]:text-red-400"]} {@attach ripple}>
            <MaterialSymbolsLogoutRounded />Log out
        </button>
    </form>
</nav>
