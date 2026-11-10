import path from "node:path";
import js from "@eslint/js";
import prettier from "eslint-config-prettier";
import svelte from "eslint-plugin-svelte";
import { defineConfig, includeIgnoreFile } from "eslint/config";
import globals from "globals";
import ts from "typescript-eslint";

export default defineConfig(
    includeIgnoreFile(path.resolve(import.meta.dirname, ".gitignore")),
    js.configs.recommended,
    ts.configs.recommended,
    svelte.configs.recommended,
    prettier,
    svelte.configs.prettier,
    {
        languageOptions: {
            globals: {
                ...globals.browser,
                ...globals.node,
            },
        },
        rules: {
            // TypeScript already reports undefined names, and this rule can't see type-only globals.
            "no-undef": "off",
            "@typescript-eslint/no-unused-vars": [
                "error",
                { ignoreRestSiblings: true, varsIgnorePattern: "^_", argsIgnorePattern: "^_", caughtErrorsIgnorePattern: "^_" },
            ],
        },
    },
    {
        files: ["**/*.svelte", "**/*.svelte.ts", "**/*.svelte.js"],
        languageOptions: {
            parserOptions: {
                parser: ts.parser,
            },
        },
        rules: {
            "@typescript-eslint/no-unused-expressions": "off",
            "svelte/no-navigation-without-resolve": "off",
        },
    },
);
