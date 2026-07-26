<div align="center">

![Square Bot](./assets/banner.gif)

# Square Bot

Advanced multipurpose discord bot for all your needs.

[![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fswayam25%2FSquare-Bot%2Fmain%2Fpyproject.toml&style=for-the-badge&logo=python&logoColor=%23FFFFFF&labelColor=%233776AB&color=%23000000)](https://www.python.org/downloads)
[![Pycord Version](https://img.shields.io/badge/pycord-v2.8.1-%23000000?style=for-the-badge&logo=python&logoColor=%23FFFFFF&labelColor=%235865F2)](https://github.com/Pycord-Development/pycord)
[![GitHub Release](https://img.shields.io/github/v/release/swayam25/Square-Bot?style=for-the-badge&logo=github&logoColor=%23FFFFFF&labelColor=%230D1117&color=%23000000)](https://github.com/swayam25/Square-Bot/releases)
[![GitHub License](https://img.shields.io/github/license/swayam25/Square-Bot?style=for-the-badge&logo=gnu&logoColor=%23FFFFFF&labelColor=%23A32D2A&color=%23000000)](https://github.com/swayam25/Square-Bot/blob/main/LICENSE)

</div>

## 🎯 Features

- Music with player controls, multi-node failover, smart autoplay & audio filters.
- Auto-mod, mass moderation, tickets & detailed logging.
- Custom emojis synced from a simple `.zip` upload.
- Browser-based database panel & live container logs.
- Fully dockerized, deploys with a single `just prod` command.

## 💫 Prerequisites

| Tool                                                                                                                                    | Type                     | Version | Purpose                                             |
| --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ------- | --------------------------------------------------- |
| [![Docker](https://img.shields.io/badge/Docker-%232560FF?style=for-the-badge&logo=docker&logoColor=%23FFFFFF)](https://www.docker.com/) | Required                 | 20.10+  | To run the bot in a containerized environment.      |
| [![Git](https://img.shields.io/badge/Git-%23F05133?style=for-the-badge&logo=git&logoColor=%23FFFFFF)](https://git-scm.com/)             | Required                 | 2.50+   | To clone the repository and manage version control. |
| [![Just](https://img.shields.io/badge/Just-%23EF4041?style=for-the-badge&logo=just&logoColor=%23FFFFFF)](https://github.com/casey/just) | Required                 | 1.27+   | A command runner for the project's recipes.         |
| [![Python](https://img.shields.io/badge/Python-%233776AB?style=for-the-badge&logo=python&logoColor=%23FFFFFF)](https://www.python.org/) | Optional (*Development*) | 3.14+   | The programming language used to develop the bot.   |
| [![UV](https://img.shields.io/badge/UV-%23DE5FE9?style=for-the-badge&logo=uv&logoColor=%23FFFFFF)](https://docs.astral.sh/uv/)          | Optional (*Development*) | 0.11+   | A modern Python package manager for development.    |

## 🚀 Production

1. Clone the repository
    ```sh
    git clone https://github.com/swayam25/Square-Bot square
    cd square
    ```

2. Create `config.toml` file from the provided `config.example.toml` and fill in the required values.
    ```sh
    cp config.example.toml config.toml
    ```

> [!TIP]
> Check [configuration](#-configuration) section for details on the configuration keys.

3. Everything is driven by `config.toml`, you don't need to touch the `Caddyfile`.
    - Set `auth-pass` to a strong password. It guards **every** web panel (*login username is `admin`*).
    - Optionally point the panels at real domains under `[domains]` to get automatic HTTPS:
        ```toml
        auth-pass = "a-strong-password"

        [domains]
        dozzle = "logs.example.com" # Dozzle
        drizzle = "db.example.com"  # Drizzle Gateway
        ```
    - Leave a domain empty to serve that panel over plain HTTP on its fallback port instead.

> [!NOTE]
> With no domain set, the panels are reachable on your server's IP:
> - Dozzle → `http://<server-ip>:8080`
> - Drizzle Gateway → `http://<server-ip>:8081`
>
> Set the matching `[domains]` key to a hostname to serve it with automatic HTTPS on `:443` instead.

4. Build the images and start everything
    ```sh
    just prod
    ```

5. Done! The bot should be up and running now. Log in with username `admin` and your `auth-pass` to reach the dozzle (`:8080` or its domain) and drizzle gateway (`:8081` or its domain).

## 🛸 Development

1. Follow the first 2 steps of the [production](#-production) section.

2. Install the dependencies and set up pre-commit hooks
    ```sh
    just setup
    ```

3. Start the docker services
    ```sh
    just start
    ```

4. Run the bot
    ```sh
    just dev
    ```
    > `just dev` auto-starts services if they aren't already running, so you can skip step 3 and run it directly.

5. Stop the docker services when done
    ```sh
    just stop
    ```

> [!IMPORTANT]
> The local stack only runs Postgres and Drizzle Gateway - no Caddy, no auth. Drizzle Gateway is exposed directly:
> - Drizzle Gateway → `http://localhost:8081`
>
> Dozzle, Caddy and the containerized bot are production-only and live in [`docker-compose.prod.yml`](./docker-compose.prod.yml).

## 📚 Setup Drizzle Gateway

1. Open the Drizzle Gateway in your browser (*`http://localhost:8081` or its domain*).
2. Log in with username `admin` and your `auth-pass`.
3. Add the Database Connection

   https://github.com/user-attachments/assets/cfbcfb0d-afa3-43b5-a502-f4e9d5962273

## 🔑 Configuration

| Key                  | Type        | Description                                                                                                       |
| -------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------- |
| `owner-id`           | `int`       | The Discord ID of the bot owner.                                                                                  |
| `owner-guild-ids`    | `list[int]` | A list of Discord IDs of the owner's guilds. Owner/Developer only commands are created only in these guilds.      |
| `system-channel-id`  | `int`       | The Discord ID of the system channel where the bot will send startup, guild join/leave etc... messages.           |
| `support-server-url` | `str`       | The invite URL of the support server.                                                                             |
| `bot-token`          | `str`       | Discord Bot Token. Get this from developer portal.                                                                |
| `database-url`       | `str`       | The URL for the PostgreSQL database.                                                                              |
| `auth-pass`          | `str`       | Single password guarding all web panels behind Caddy. Login username is `admin`.                                  |
| `domains.dozzle`     | `str`       | Hostname for the Dozzle.                                                                                          |
| `domains.drizzle`    | `str`       | Hostname for the Drizzle Gateway.                                                                                 |
| `colors.theme`       | `str`       | The color theme for the bot's view containers.                                                                    |
| `colors.green`       | `str`       | The color code for green color in view containers.                                                                |
| `colors.red`         | `str`       | The color code for red color in view containers.                                                                  |
| `colors.orange`      | `str`       | The color code for orange color in view containers.                                                               |
| `[[lavalink]]`       | `table`     | A Lavalink node. Multiple `[[lavalink]]` tables can be configured, players fail over to another node if one dies. |
| `lavalink.host`      | `str`       | The host of the Lavalink server.                                                                                  |
| `lavalink.port`      | `int`       | The port of the Lavalink server.                                                                                  |
| `lavalink.password`  | `str`       | The password for the Lavalink server.                                                                             |
| `lavalink.region`    | `str`       | The region of the Lavalink server. This is used for latency-based node selection. Set `""` for auto-selection.    |
| `lavalink.secure`    | `bool`      | Whether to use secure connection (wss) for Lavalink.                                                              |

## ✨ Custom Emojis

The bot ships with a default set of Unicode emojis defined on the `Emoji` class in [`emoji.py`](./utils/emoji.py). You can override any of these with your own Discord custom emojis.

**How it works:** every emoji is keyed by an attribute name on the `Emoji` class (*e.g. `success`, `error`, `loading`*). The bot loads overrides from `.cache/emoji.json`, matching each entry to an attribute by name. Any attribute without an override simply falls back to its default.

There are two ways to provide overrides - upload a `.zip`, or write `.cache/emoji.json` by hand.

### [Option 1] Upload a `.zip` (*recommended*)

The workflow is the same whether you use the emojis bundled with this bot or your own:

1. **Prepare a `.zip`** of `.png`/`.gif` emoji files. Each file name **must** match an attribute on the `Emoji` class (*e.g. `success.png` → the `success` attribute*).
    > To use the bot's built-in set, just grab the ready-made [`emojis.zip`](./assets/emojis.zip).
1. **`/emoji upload`**: Upload the `.zip` to register the emojis with Discord.

```mermaid
flowchart LR
    A["Zip of .png/.gif files<br/>named after Emoji attributes"] --> B["/emoji upload"]
    B --> C[".cache/emoji.json"]
    C --> D["Emojis applied ✨"]
```

### [Option 2] Write `.cache/emoji.json` manually

If you already have the emojis, you can skip uploading and create `.cache/emoji.json` yourself:

```json
{
    "emoji_name": "<a:dc_emoji_name:dc_emoji_id>",
    "emoji_name": "<:dc_emoji_name:dc_emoji_id>"
}
```

| Field                | Meaning                                                           |
| -------------------- | ----------------------------------------------------------------- |
| `emoji_name`         | The attribute name on the `Emoji` class this override maps to.    |
| `<a:...>` / `<:...>` | `<a:...>` is an **animated** emoji, `<:...>` is a **static** one. |
| `dc_emoji_name`      | The emoji's name as it appears in Discord.                        |
| `dc_emoji_id`        | The emoji's unique Discord ID.                                    |

## ❤️ Contributing

Contributions are welcome! Whether it's a bug fix, a new feature, or a docs tweak, here's how to get set up and what we look for.

### Getting started

1. Fork the repository and clone your fork.
2. Set up your development environment by following the [development](#-development) section.
3. Create a branch for your change, commit your work, and open a pull request.

### Guidelines

- **Commits**: Write clear, meaningful messages that describe *what* changed and *why*, and follow the style used in the project's history.
- **Code quality**: Keep the code clean, readable, and consistent with the surrounding style. Let the `pre-commit` hooks format and lint your changes before you push.
- **Testing**: Run the bot locally and confirm your change works as expected before opening a PR.
