<script lang="ts">
    import square from "#lib/assets/square.svg";
    import { openInvitePopup } from "#lib/auth.ts";
    import FooterLedge from "#lib/components/site/FooterLedge.svelte";
    import type { Component } from "svelte";
    import MaterialSymbolsAccountCircleRounded from "~icons/material-symbols/account-circle-rounded";
    import MaterialSymbolsBugReportRounded from "~icons/material-symbols/bug-report-rounded";
    import MaterialSymbolsCodeBlocksRounded from "~icons/material-symbols/code-blocks-rounded";
    import MaterialSymbolsDashboardRounded from "~icons/material-symbols/dashboard-rounded";
    import ThesvgDiscord from "~icons/thesvg/discord";
    import ThesvgGit from "~icons/thesvg/git";
    import ThesvgGithub from "~icons/thesvg/github";

    let { inviteUrl, installUrl }: { inviteUrl: string; installUrl: string } = $props();

    type Link = { href: string; label: string; icon: Component; popup?: boolean; external?: boolean };

    const REPO = "https://github.com/swayam25/Square-Bot";
    const columns: Link[][] = $derived([
        [
            { href: inviteUrl, label: "Add to server", icon: ThesvgDiscord, popup: true },
            { href: installUrl, label: "Add to account", icon: MaterialSymbolsAccountCircleRounded, popup: true },
            { href: "/guild", label: "Dashboard", icon: MaterialSymbolsDashboardRounded },
            { href: "/commands", label: "Commands", icon: MaterialSymbolsCodeBlocksRounded },
        ],
        [
            { href: REPO, label: "GitHub", icon: ThesvgGithub, external: true },
            { href: `${REPO}/issues/new`, label: "Report a bug", icon: MaterialSymbolsBugReportRounded, external: true },
        ],
    ]);
</script>

<footer class="mt-12 overflow-x-clip">
    <div class="mx-auto max-w-6xl px-4 md:px-6">
        <FooterLedge />
    </div>
    <div class="bg-gray-900">
        <div class="mx-auto flex max-w-6xl flex-col gap-8 px-4 pt-8 md:flex-row md:items-start md:justify-between md:px-6">
            <div class="flex flex-col gap-4">
                <a href="/" class="flex w-fit items-center gap-2">
                    <img src={square} alt="" class="size-8" />
                    <span class="font-display text-2xl font-semibold">Square</span>
                </a>
                <p class="flex items-center gap-1.5 font-mono text-sm text-gray-400">
                    <ThesvgGit class="size-4 shrink-0" />Open source Discord bot
                </p>
            </div>
            <nav aria-label="Footer" class="flex w-fit gap-x-8 font-mono text-sm">
                {#each columns as column, index (index)}
                    <div class="flex flex-col gap-4">
                        {#each column as link (link.label)}
                            <a
                                href={link.href}
                                target={link.popup || link.external ? "_blank" : undefined}
                                rel={link.popup ? "noopener" : link.external ? "noopener noreferrer" : undefined}
                                onclick={link.popup ? openInvitePopup : undefined}
                                class="flex items-center gap-2 text-gray-400 duration-200 hover:text-gray-100"
                                ><link.icon class="size-4" />{link.label}</a
                            >
                        {/each}
                    </div>
                {/each}
            </nav>
        </div>

        <p class="mx-auto flex max-w-6xl items-center gap-1 px-4 pt-16 pb-8 font-mono text-xs text-gray-500 md:px-6">
            <span class="text-base leading-none">©</span>{new Date().getFullYear()} Square. Not affiliated with Discord.
        </p>
    </div>
</footer>
