import { randomBytes } from "node:crypto";
import { existsSync } from "node:fs";
import { chmod, readFile, writeFile } from "node:fs/promises";
import { cancel, confirm, intro, isCancel, log, multiselect, note, outro, password, select, text } from "@clack/prompts";
import type { CANCEL_SYMBOL } from "@clack/prompts";
import { parse, stringify } from "smol-toml";

const dev = process.argv.includes("--dev");
const root = new URL("../", import.meta.url);
const files = {
    example: new URL("apps/bot/config.example.toml", root),
    bot: new URL("apps/bot/config.toml", root),
    env: new URL(dev ? "apps/web/.env" : "apps/web/.env.production", root),
};
const SNOWFLAKE = /^\d{17,20}$/;
const ID_ERROR = "A Discord ID is 17 to 20 digits";

function answer<T>(value: T | typeof CANCEL_SYMBOL): T {
    if (isCancel(value)) {
        cancel("Cancelled, nothing was written");
        process.exit(130);
    }
    return value;
}

function matches(pattern: RegExp, message: string) {
    return (value: string | undefined) => (pattern.test(value ?? "") ? undefined : message);
}

async function ask(message: string, pattern: RegExp, error: string, initialValue?: string) {
    return answer(await text({ message, initialValue, validate: matches(pattern, error) }));
}

async function askSecret(message: string, pattern: RegExp, error: string) {
    return answer(await password({ message, validate: matches(pattern, error) }));
}

// A bot token starts with the bot's user ID in base64url, which is also its application ID
function applicationId(token: string) {
    const id = Buffer.from(token.split(".")[0], "base64url").toString();
    return SNOWFLAKE.test(id) ? id : undefined;
}

function relative(file: URL) {
    return file.pathname.slice(root.pathname.length);
}

async function writePrivate(file: URL, content: string) {
    await writeFile(file, content, { mode: 0o600 });
    await chmod(file, 0o600);
}

intro(` Square ${dev ? "development" : "production"} setup `);

const existing = [files.bot, files.env].filter(existsSync).map(relative);
if (existing.length) {
    const overwrite = answer(await confirm({ message: `${existing.join(" and ")} already exist. Overwrite?`, initialValue: false }));
    if (!overwrite) {
        outro("Kept the existing config");
        process.exit(0);
    }
}

const config = parse(await readFile(files.example, "utf8"), { integersAsBigInt: "asNeeded" }) as Record<string, any>;

log.step("Discord, from the Developer Portal");
const token = await askSecret("Bot token", /^[\w-]+\.[\w-]+\.[\w-]+$/, "Paste the token from the Bot page");
const clientSecret = await askSecret("OAuth2 client secret", /^[\w-]+$/, "Paste the secret from the OAuth2 page");
const clientId = applicationId(token) ?? (await ask("Application ID", SNOWFLAKE, ID_ERROR));
config["bot-token"] = token;
config["owner-id"] = BigInt(await ask("Your user ID", SNOWFLAKE, ID_ERROR));
const guilds = await ask(
    "Owner server IDs, comma separated",
    /^\d{17,20}(\s*,\s*\d{17,20})*$/,
    "Discord IDs of 17 to 20 digits, separated by commas",
);
config["owner-guild-ids"] = guilds.split(",").map((id) => BigInt(id.trim()));
config["system-channel-id"] = BigInt(await ask("System channel ID for startup and join logs", SNOWFLAKE, ID_ERROR));
if (!dev) {
    const url = await ask("Dashboard URL", /^https?:\/\/[^\s"\\]+$/, "A URL like https://square.example.com", "https://");
    config["dashboard-url"] = url.replace(/\/+$/, "");
}

log.step("Lavalink, the node that plays music");
config.lavalink = [];
do {
    config.lavalink.push({
        host: await ask("Host", /^[\w.-]+$/, "A hostname or IP"),
        port: Number(await ask("Port", /^\d{1,5}$/, "A port number", "2333")),
        password: await askSecret("Password", /.+/, "The node's password"),
        secure: answer(await confirm({ message: "Uses SSL?", initialValue: false })),
        regions: [],
    });
} while (answer(await confirm({ message: "Add another node?", initialValue: false })));

log.step("Options");
config["log-level"] = answer(
    await select({
        message: "Log level",
        initialValue: "INFO",
        options: ["DEBUG", "INFO", "WARNING", "ERROR"].map((value) => ({ value })),
    }),
);
const extras = answer(
    await multiselect({
        message: "Extras",
        required: false,
        initialValues: dev ? ["docs"] : [],
        options: [
            { value: "log-file", label: "Write logs to .cache/logs" },
            { value: "docs", label: "Serve API docs at /docs" },
        ],
    }),
);
config["log-file"] = extras.includes("log-file");

const secret = randomBytes(32).toString("hex");
config.api = { ...config.api, secret, docs: extras.includes("docs") };
const env = {
    ...(dev && { BOT_API_URL: "http://127.0.0.1:8080" }),
    BOT_API_SECRET: secret,
    ...(dev && { REDIS_URL: "redis://127.0.0.1:6379" }),
    DISCORD_CLIENT_ID: clientId,
    DISCORD_CLIENT_SECRET: clientSecret,
};

await writePrivate(files.bot, `${stringify(config).trimEnd()}\n`);
await writePrivate(
    files.env,
    Object.entries(env)
        .map(([key, value]) => `${key}=${value}\n`)
        .join(""),
);

note(`Add ${config["dashboard-url"]}/auth/callback as an OAuth2 redirect in the Developer Portal`, "Discord");
outro(`Wrote ${relative(files.bot)} and ${relative(files.env)}. Then run ${dev ? "just dev" : "just up"}`);
