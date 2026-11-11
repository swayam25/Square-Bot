<script lang="ts">
    import square from "#lib/assets/square.svg";
    import { openLoginPopup } from "#lib/auth.ts";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Popup from "#lib/components/ui/Popup.svelte";
    import { ripple } from "#lib/motion.ts";
    import { page } from "$app/state";
    import MaterialSymbolsLoginRounded from "~icons/material-symbols/login-rounded";
    import MaterialSymbolsLogoutRounded from "~icons/material-symbols/logout-rounded";
    import MaterialSymbolsPlayShapesRounded from "~icons/material-symbols/play-shapes-rounded";

    const user = $derived(page.data.user);
</script>

<header class="pointer-events-none fixed inset-x-0 top-0 z-40 px-4 pt-4">
    <nav
        class="pointer-events-auto mx-auto flex h-16 max-w-6xl items-center gap-2 rounded-full bg-mist-950/70 p-2 shadow-lg shadow-black/20 backdrop-blur-xl"
    >
        <a href="/" class="ripple flex h-12 items-center gap-2 rounded-full pr-4 pl-2 hover:bg-surface-2" aria-label="Square home" {@attach ripple}>
            <img src={square} alt="" class="size-8" />
            <span class="font-display text-xl font-semibold">Square</span>
        </a>
        <span class="flex-1"></span>
        {#if user}
            <Popup
                title="Your account"
                triggerClass="flex size-12 transition-opacity hover:opacity-80 items-center justify-center rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
                {#snippet trigger()}
                    <Avatar src={user.avatarUrl} name={user.name} class="size-12" />
                {/snippet}
                <div class="flex items-center gap-4 p-2 pb-4">
                    <Avatar src={user.avatarUrl} name={user.name} class="size-12" />
                    <div class="flex min-w-0 flex-col">
                        <span class="truncate font-semibold">{user.name}</span>
                        <span class="truncate font-mono text-sm text-mist-400">@{user.username}</span>
                    </div>
                </div>
                <nav class="flex flex-col gap-1">
                    <a
                        href="/guild"
                        class="ripple flex h-10 items-center gap-4 rounded-xl px-4 text-sm font-medium hover:bg-white/10"
                        {@attach ripple}
                    >
                        <MaterialSymbolsPlayShapesRounded class="size-5 text-mist-400" />Your servers
                    </a>
                    <form method="POST" action="/logout">
                        <button
                            class="ripple flex h-10 w-full items-center gap-4 rounded-xl px-4 text-sm font-medium text-red-400 hover:bg-red-400/10"
                            {@attach ripple}
                        >
                            <MaterialSymbolsLogoutRounded class="size-5" />Log out
                        </button>
                    </form>
                </nav>
            </Popup>
        {:else}
            <Button href="/login" data-sveltekit-reload onclick={(event) => openLoginPopup() && event.preventDefault()}>
                <MaterialSymbolsLoginRounded />Log in
            </Button>
        {/if}
    </nav>
</header>
