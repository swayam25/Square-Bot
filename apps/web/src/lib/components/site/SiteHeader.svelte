<script lang="ts">
    import square from "#lib/assets/square.svg";
    import { ripple } from "#lib/attachments/ripple.ts";
    import { openLoginPopup } from "#lib/auth.ts";
    import AccountMenu from "#lib/components/site/AccountMenu.svelte";
    import Avatar from "#lib/components/ui/Avatar.svelte";
    import Button from "#lib/components/ui/Button.svelte";
    import Popup from "#lib/components/ui/Popup.svelte";
    import { focusRing, menuRow } from "#lib/components/ui/styles.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { mobile } from "#lib/media.ts";
    import { page } from "$app/state";
    import MaterialSymbolsCodeBlocksRounded from "~icons/material-symbols/code-blocks-rounded";
    import MaterialSymbolsLoginRounded from "~icons/material-symbols/login-rounded";
    import MaterialSymbolsPlayShapesRounded from "~icons/material-symbols/play-shapes-rounded";

    const user = $derived(page.data.user);
</script>

<header class="pointer-events-none fixed inset-x-0 top-0 z-40 px-4 pt-4">
    <nav
        class="pointer-events-auto mx-auto flex h-16 max-w-6xl items-center gap-2 rounded-card bg-gray-950/70 p-2 shadow-lg shadow-black/20 backdrop-blur-xl"
    >
        <a href="/" class="ripple flex h-12 items-center gap-2 rounded-control-lg pr-4 pl-2 hover:bg-gray-800" {@attach ripple}>
            <img src={square} alt="" class="size-8" />
            <span class="font-display text-xl font-semibold">Square</span>
        </a>
        <span class="flex-1"></span>
        <Tooltip content={mobile.current ? "Commands" : null}>
            <Button variant="ghost" href="/commands" class="max-md:w-12 max-md:px-0">
                <MaterialSymbolsCodeBlocksRounded /><span class="max-md:sr-only">Commands</span>
            </Button>
        </Tooltip>
        {#if user}
            <Popup
                title="Your account"
                triggerClass={["flex size-12 items-center justify-center rounded-icon transition-opacity hover:opacity-80", focusRing]}
            >
                {#snippet trigger()}
                    <Avatar src={user.avatarUrl} name={user.name} class="size-12" />
                {/snippet}
                <AccountMenu {user}>
                    <a href="/guild" class={menuRow} {@attach ripple}><MaterialSymbolsPlayShapesRounded />Your servers</a>
                </AccountMenu>
            </Popup>
        {:else}
            <Button href="/login" data-sveltekit-reload onclick={(event) => openLoginPopup() && event.preventDefault()}>
                <MaterialSymbolsLoginRounded />Log in
            </Button>
        {/if}
    </nav>
</header>
