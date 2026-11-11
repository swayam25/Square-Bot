<script lang="ts">
    import Logo from "#lib/components/Logo.svelte";
    import SimpleIconsDiscord from "~icons/simple-icons/discord";
    import SimpleIconsGithub from "~icons/simple-icons/github";
    import SimpleIconsOpensourceinitiative from "~icons/simple-icons/opensourceinitiative";
    import TablerBug from "~icons/tabler/bug";
    import TablerLayoutDashboard from "~icons/tabler/layout-dashboard";

    let { inviteUrl }: { inviteUrl: string } = $props();

    const REPO = "https://github.com/swayam25/Square-Bot";
    const links = $derived([
        { href: inviteUrl, label: "Add to Discord", icon: SimpleIconsDiscord },
        { href: "/servers", label: "Dashboard", icon: TablerLayoutDashboard },
        { href: REPO, label: "GitHub", icon: SimpleIconsGithub },
        { href: `${REPO}/issues/new`, label: "Report a bug", icon: TablerBug },
    ]);
</script>

<footer class="relative mt-12 overflow-hidden rounded-t-[40px] bg-surface-1">
    <div class="mx-auto flex max-w-6xl flex-col gap-8 px-4 pt-16 md:flex-row md:items-start md:justify-between md:px-6">
        <div class="flex flex-col gap-4">
            <a href="/" class="flex w-fit items-center gap-2">
                <Logo class="size-10" />
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
        <span>Made with love</span>
    </div>

    <!-- The wordmark sinks off the bottom edge. Each letter hops when the pointer passes over it -->
    <div aria-hidden="true" class="flex justify-center pt-4 select-none">
        {#each [..."SQUARE"] as letter, index (index)}
            <span
                class="inline-block translate-y-[18%] font-display text-[22vw] leading-[0.8] font-bold text-surface-2 transition-[translate,color] duration-400 ease-spring hover:translate-y-0 hover:text-accent/20 lg:text-[256px]"
            >
                {letter}
            </span>
        {/each}
    </div>
</footer>
