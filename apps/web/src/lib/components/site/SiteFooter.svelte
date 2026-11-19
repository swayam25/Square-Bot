<script lang="ts">
    import square from "#lib/assets/square.svg";
    import { openInvitePopup } from "#lib/auth.ts";
    import FooterLedge from "#lib/components/site/FooterLedge.svelte";
    import MaterialSymbolsBugReportRounded from "~icons/material-symbols/bug-report-rounded";
    import MaterialSymbolsCodeBlocksRounded from "~icons/material-symbols/code-blocks-rounded";
    import MaterialSymbolsDashboardRounded from "~icons/material-symbols/dashboard-rounded";
    import SimpleIconsDiscord from "~icons/simple-icons/discord";
    import SimpleIconsGit from "~icons/simple-icons/git";
    import SimpleIconsGithub from "~icons/simple-icons/github";

    let { inviteUrl }: { inviteUrl: string } = $props();

    const REPO = "https://github.com/swayam25/Square-Bot";
    const links = $derived([
        { href: inviteUrl, label: "Add to Discord", icon: SimpleIconsDiscord, popup: true },
        { href: "/guild", label: "Dashboard", icon: MaterialSymbolsDashboardRounded },
        { href: "/commands", label: "Commands", icon: MaterialSymbolsCodeBlocksRounded },
        { href: REPO, label: "GitHub", icon: SimpleIconsGithub, external: true },
        { href: `${REPO}/issues/new`, label: "Report a bug", icon: MaterialSymbolsBugReportRounded, external: true },
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
                    <SimpleIconsGit class="size-4 shrink-0" />Open source Discord bot
                </p>
            </div>
            <nav aria-label="Footer" class="grid w-fit grid-flow-col grid-rows-3 gap-x-8 gap-y-4 font-mono text-sm">
                {#each links as link (link.label)}
                    <a
                        href={link.href}
                        target={link.popup || link.external ? "_blank" : undefined}
                        rel={link.popup ? "noopener" : link.external ? "noopener noreferrer" : undefined}
                        onclick={link.popup ? openInvitePopup : undefined}
                        class="flex items-center gap-2 text-gray-400 duration-200 hover:text-gray-100"><link.icon class="size-4" />{link.label}</a
                    >
                {/each}
            </nav>
        </div>

        <p class="mx-auto flex max-w-6xl items-center gap-1 px-4 pt-16 pb-8 font-mono text-xs text-gray-500 md:px-6">
            <span class="text-base leading-none">©</span>{new Date().getFullYear()} Square. Not affiliated with Discord.
        </p>
    </div>
</footer>
