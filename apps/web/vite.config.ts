import adapter from "@sveltejs/adapter-node";
import { sveltekit } from "@sveltejs/kit/vite";
import tailwindcss from "@tailwindcss/vite";
import Icons from "unplugin-icons/vite";
import { defineConfig } from "vite";

export default defineConfig({
    plugins: [
        tailwindcss(),
        Icons({ compiler: "svelte" }),
        sveltekit({
            compilerOptions: {
                // Force runes mode for the project, except for libraries. Can be removed in svelte 6.
                runes: ({ filename }) => (filename.split(/[/\\]/).includes("node_modules") ? undefined : true),
            },
            adapter: adapter(),
            csp: {
                mode: "auto",
                directives: {
                    "default-src": ["self"],
                    "script-src": ["self"],
                    // Svelte transitions and `style:` directives write inline styles
                    "style-src": ["self", "unsafe-inline"],
                    // Covers and avatars come from Discord and every music service's CDN
                    "img-src": ["self", "data:", "blob:", "https:"],
                    // Transcript videos come from Discord's CDN, and GIF embeds from hosts like Tenor
                    "media-src": ["self", "https:"],
                    "font-src": ["self", "data:"],
                    "connect-src": ["self"],
                    "frame-src": ["https://www.youtube-nocookie.com"],
                    "frame-ancestors": ["none"],
                    "form-action": ["self"],
                    "base-uri": ["self"],
                    "object-src": ["none"],
                },
            },
            experimental: { remoteFunctions: true },
        }),
    ],
});
