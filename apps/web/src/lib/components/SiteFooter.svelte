<script module lang="ts">
    const W = 1440;
    const H = 96;

    function wave(base: number, amplitude: number, wavelength: number, phase = 0) {
        let d = `M0 ${H}`;
        for (let x = 0; x <= W; x += 8) d += `L${x} ${(base - amplitude * Math.sin(((x + phase) / wavelength) * 2 * Math.PI)).toFixed(1)}`;
        return `${d}L${W} ${H}Z`;
    }

    const BACK = wave(36, 18, 360, 120);
    const FRONT = wave(56, 14, 480);
</script>

<script lang="ts">
    import square from "#lib/assets/square.svg";
    import MaterialSymbolsBugReportRounded from "~icons/material-symbols/bug-report-rounded";
    import MaterialSymbolsDashboardRounded from "~icons/material-symbols/dashboard-rounded";
    import SimpleIconsDiscord from "~icons/simple-icons/discord";
    import SimpleIconsGithub from "~icons/simple-icons/github";
    import SimpleIconsOpensourceinitiative from "~icons/simple-icons/opensourceinitiative";

    let { inviteUrl }: { inviteUrl: string } = $props();

    const REPO = "https://github.com/swayam25/Square-Bot";
    const links = $derived([
        { href: inviteUrl, label: "Add to Discord", icon: SimpleIconsDiscord },
        { href: "/servers", label: "Dashboard", icon: MaterialSymbolsDashboardRounded },
        { href: REPO, label: "GitHub", icon: SimpleIconsGithub },
        { href: `${REPO}/issues/new`, label: "Report a bug", icon: MaterialSymbolsBugReportRounded },
    ]);
</script>

<footer class="mt-12">
    <svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" aria-hidden="true" class="-mb-px block h-16 w-full md:h-24">
        <path d={BACK} class="fill-accent/10" />
        <path d={FRONT} class="fill-surface-1" />
    </svg>
    <div class="relative overflow-hidden bg-surface-1">
        <div class="mx-auto flex max-w-6xl flex-col gap-8 px-4 pt-16 md:flex-row md:items-start md:justify-between md:px-6">
            <div class="flex flex-col gap-4">
                <a href="/" class="flex w-fit items-center gap-2">
                    <img src={square} alt="" class="size-8" />
                    <span class="font-display text-2xl font-semibold">Square</span>
                </a>
                <span class="flex gap-1 text-mist-400">
                    <SimpleIconsOpensourceinitiative class="size-4" />
                    <p class="max-w-xs text-xs">Open source discord bot</p>
                </span>
            </div>
            <nav aria-label="Footer" class="grid w-fit grid-cols-2 gap-x-8 gap-y-4 text-sm">
                {#each links as link (link.label)}
                    <a href={link.href} class="flex items-center gap-2 text-mist-400 duration-200 hover:text-mist-100"
                        ><link.icon class="size-4" />{link.label}</a
                    >
                {/each}
            </nav>
        </div>

        <div class="mx-auto flex max-w-6xl flex-col gap-2 px-4 pt-12 text-xs text-mist-500 sm:flex-row sm:justify-between md:px-6">
            <span>© {new Date().getFullYear()} Square. Not affiliated with Discord.</span>
        </div>

        <div aria-hidden="true" class="flex justify-center pt-4 select-none">
            {#each [..."SQUARE"] as letter, index (index)}
                <span
                    class="inline-block translate-y-[18%] font-display text-[22vw] leading-[0.8] font-bold text-surface-2 transition-[translate,color] duration-400 ease-spring hover:translate-y-0 hover:text-accent/20 lg:text-[256px]"
                >
                    {letter}
                </span>
            {/each}
        </div>
    </div>
</footer>
