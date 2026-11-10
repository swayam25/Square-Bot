import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
    input: "./openapi.json",
    output: { path: "./src/gen", postProcess: ["prettier"] },
    plugins: ["@hey-api/typescript", "@hey-api/client-fetch", "@hey-api/sdk", "zod"],
});
