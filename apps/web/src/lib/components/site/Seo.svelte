<script lang="ts">
    import banner from "#lib/assets/banner.gif";
    import square from "#lib/assets/square.svg";
    import { page } from "$app/state";
    import type { APIComponentEmbed, APIComponentEmbedButton, APIMessageComponentEmoji } from "discord-api-types/v10";

    const SITE = "Square";
    const TAGLINE = "The one Discord bot you need";

    let { title, description, noindex = false }: { title?: string; description?: string; noindex?: boolean } = $props();

    const origin = $derived(page.url.origin);
    const url = $derived(origin + (page.url.pathname === "/" ? "/" : page.url.pathname.replace(/\/$/, "")));
    const image = $derived(new URL(banner, origin).href);
    const hidden = $derived(noindex || page.status >= 400 || /^\/(guild|auth)(\/|$)/.test(page.route.id ?? ""));

    function button(label: string, href: string | undefined, emoji: APIMessageComponentEmoji | undefined): APIComponentEmbedButton[] {
        return href ? [{ type: 2, style: 5, label, url: href, ...(emoji && { emoji }) }] : [];
    }

    const card: APIComponentEmbed = $derived({
        component: {
            type: 17,
            accent_color: 0x1fceec,
            components: [
                { type: 12, items: [{ media: { url: image }, description: `${SITE} banner` }] },
                { type: 10, content: `## [${title ?? SITE}](${url})\n${TAGLINE}${description ? `\n-# ${description}` : ""}` },
                {
                    type: 1,
                    components: [
                        ...button("Add to Discord", page.data.inviteUrl, page.data.squareEmojis?.user_add_white),
                        ...button("Open dashboard", `${origin}/guild`, page.data.squareEmojis?.settings_white),
                    ],
                },
            ],
        },
    });

    // `<` is escaped so a value can't close the script tag early
    const json = (value: unknown) => JSON.stringify(value).replace(/</g, "\\u003c");
    const website = $derived(json({ "@context": "https://schema.org", "@type": "WebSite", name: SITE, url: `${origin}/` }));
</script>

<svelte:head>
    <title>{title ? `${title} · ${SITE}` : `${SITE} · ${TAGLINE}`}</title>
    <meta name="description" content={description ?? TAGLINE} />
    <meta name="robots" content={hidden ? "noindex, nofollow" : "index, follow, max-image-preview:large"} />
    {#if !hidden}<link rel="canonical" href={url} />{/if}
    <link rel="icon" href={square} type="image/svg+xml" />
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
    <meta name="theme-color" content="#030712" />

    <meta property="og:type" content="website" />
    <meta property="og:site_name" content={SITE} />
    <meta property="og:url" content={url} />
    <meta property="og:title" content={title ?? SITE} />
    <meta property="og:description" content={description ?? TAGLINE} />
    <meta property="og:image" content={image} />
    <meta property="og:image:type" content="image/gif" />
    <meta property="og:image:width" content="1280" />
    <meta property="og:image:height" content="640" />
    <meta property="og:image:alt" content="{SITE} banner" />
    <meta name="twitter:card" content="summary_large_image" />

    <!-- eslint-disable svelte/no-at-html-tags -->
    {#if !hidden && page.url.pathname === "/"}
        {@html `<script type="application/ld+json">${website}<` + "/script>"}
    {/if}
    {@html `<script id="discord:component-embed" type="application/json">${json(card)}<` + "/script>"}
    <!-- eslint-enable svelte/no-at-html-tags -->
</svelte:head>
