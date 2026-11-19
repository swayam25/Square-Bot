<script module lang="ts">
    const W = 1440;
    const H = 96;

    const WAVELENGTH = 480;
    const AMPLITUDE = 10;
    const BASE = 56;

    // One wavelength wider than the box, so drifting by exactly one wavelength loops without a seam
    let d = `M0 ${H}`;
    for (let x = 0; x <= W + WAVELENGTH; x += 8) d += `L${x} ${(BASE - AMPLITUDE * Math.sin((x / WAVELENGTH) * 2 * Math.PI)).toFixed(1)}`;
    const WAVE = `${d}L${W + WAVELENGTH} ${H}Z`;
</script>

<script lang="ts">
    import square from "#lib/assets/square.svg";
    import { openInvitePopup } from "#lib/auth.ts";
    import FooterWordmark from "#lib/components/site/FooterWordmark.svelte";
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

<footer class="mt-12">
    <svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" aria-hidden="true" class="-mb-px block h-16 w-full md:h-24">
        <path d={WAVE} class="drift fill-gray-900" />
    </svg>
    <div class="relative overflow-hidden bg-gray-900">
        <div class="mx-auto flex max-w-6xl flex-col gap-8 px-4 pt-16 md:flex-row md:items-start md:justify-between md:px-6">
            <div class="flex flex-col gap-4">
                <a href="/" class="flex w-fit items-center gap-2">
                    <img src={square} alt="" class="size-8" />
                    <span class="font-display text-2xl font-semibold">Square</span>
                </a>
                <p class="flex items-center gap-1.5 text-sm text-gray-400">
                    <SimpleIconsGit class="size-4 shrink-0" />Open source Discord bot
                </p>
            </div>
            <nav aria-label="Footer" class="grid w-fit grid-flow-col grid-rows-3 gap-x-8 gap-y-4 text-sm">
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

        <div class="mx-auto max-w-6xl px-4 pt-16 md:px-6">
            <FooterWordmark />
        </div>

        <div class="mx-auto max-w-6xl px-4 pt-4 pb-8 text-xs text-gray-500 md:px-6">
            © {new Date().getFullYear()} Square. Not affiliated with Discord.
        </div>
    </div>
</footer>

<style>
    .drift {
        animation: drift 20s linear infinite;
    }
    @keyframes drift {
        to {
            transform: translateX(-480px);
        }
    }
    @media (prefers-reduced-motion: reduce) {
        .drift {
            animation: none;
        }
    }
</style>
