/** @type {import("prettier").Config} */
const config = {
    tabWidth: 4,
    printWidth: 150,
    // The Tailwind plugin must stay last, it wraps the other plugins' printers.
    plugins: ["prettier-plugin-svelte", "@ianvs/prettier-plugin-sort-imports", "prettier-plugin-tailwindcss"],
    importOrder: ["^[#$]", "^[@]", "^[a-z]", "^[~]", "^[.]"],
    importOrderSafeSideEffects: ["^.*\\.css$"],
    // Tailwind v4 has no JS config, so class sorting reads the theme from this entry stylesheet.
    tailwindStylesheet: "./apps/web/src/routes/layout.css",
    overrides: [
        {
            files: ["*.yml", "*.yaml"],
            options: {
                tabWidth: 2,
            },
        },
    ],
};

export default config;
