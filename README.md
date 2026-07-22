<div align="center">

![Square Bot](./assets/banner.gif)

# Square Bot

Advanced multipurpose discord bot for all your needs.

[![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fswayam25%2FSquare-Bot%2Fmain%2Fpyproject.toml&style=for-the-badge&logo=python&logoColor=%23FFFFFF&labelColor=%233776AB&color=%23000000)](https://www.python.org/downloads)
[![Pycord Version](https://img.shields.io/badge/pycord-v2.7.1-%23000000?style=for-the-badge&logo=python&logoColor=%23FFFFFF&labelColor=%235865F2)](https://github.com/Pycord-Development/pycord)
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
| [![Python](https://img.shields.io/badge/Python-%233776AB?style=for-the-badge&logo=python&logoColor=%23FFFFFF)](https://www.python.org/) | Optional (*Development*) | 3.12+   | The programming language used to develop the bot.   |
| [![UV](https://img.shields.io/badge/UV-%23DE5FE9?style=for-the-badge&logo=uv&logoColor=%23FFFFFF)](https://docs.astral.sh/uv/)          | Optional (*Development*) | 0.9+    | A modern Python package manager for development.    |

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
> - Dozzle → `http://<server-ip>:8081`
> - Drizzle Gateway → `http://<server-ip>:8080`
>
> Set the matching `[domains]` key to a hostname to serve it with automatic HTTPS on `:443` instead.

4. Build the images and start everything
    ```sh
    just prod
    ```

5. Done! The bot should be up and running now. Log in with username `admin` and your `auth-pass` to reach the database panel (`:8080` or its domain) and container logs (`:8081` or its domain).

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
> - Drizzle Gateway → `http://localhost:8080`
>
> Dozzle, Caddy and the containerized bot are production-only and live in `docker-compose.prod.yml`.

## 📚 Setup Drizzle Gateway

1. Open the Drizzle Gateway panel in your browser (*`http://localhost:8080` or its domain*).
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
| `auth-pass`          | `str`       | Single password guarding all web panels (database & logs) behind Caddy. Login username is `admin`.                |
| `domains.dozzle`     | `str`       | Hostname for the Dozzle container-logs panel.                                                                     |
| `domains.drizzle`    | `str`       | Hostname for the Drizzle Gateway database panel.                                                                  |
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

## ✨ Using Custom Emojis

- To create custom emojis, upload a `.zip` file containing the emojis (*`.png` format*) using `/emoji upload` command.
- There is a zip file containing custom emojis that are used in this bot.
- Upload the [`emojis.zip`](./assets/emojis.zip) via `/emoji upload` command.
- Run the `/emoji sync` command to sync the emojis to `.cache/emoji.json`.
- Restart the bot to apply the changes.

## 🙂 Using Your Own Emojis

- Emojis are synced (*when you run the `/emoji sync` command*) based on their file names, which must match the attribute names of the `Emoji` class in [`emoji.py`](./utils/emoji.py).
- Collect all the emojis you want the bot to use and name each file according to the corresponding attribute in the `Emoji` class.
- Compress all the emoji files into a single `.zip` archive.
- Upload this archive using the `/emoji upload` command.
- After uploading, run the `/emoji sync` command to sync the emojis to `.cache/emoji.json`.
- Restart the bot to apply the changes.

Alternatively, you can manually create a `.cache/emoji.json` file with the following structure:
```json
{
    "emoji_name": "<a:dc_emoji_name:dc_emoji_id>",
    "emoji_name": "<:dc_emoji_name:dc_emoji_id>"
}
```
- `emoji_name` must match the corresponding attribute name in the `Emoji` class.
- `<a:...>` denotes an animated emoji, while `<:...>` denotes a static emoji.
- `dc_emoji_name` refers to the name of the emoji as it appears in Discord.
- `dc_emoji_id` is the unique identifier of the emoji in Discord.

> [!NOTE]
> If a custom emoji is missing for any attribute in `.cache/emoji.json`, the bot will automatically use the default emoji from the `Emoji` class.

## ❤️ Contributing

- Things to keep in mind
    - Follow our commit message convention.
    - Write meaningful commit messages.
    - Keep the code clean and readable.
    - Make sure the bot is working as expected.

- Install dependencies and set up `pre-commit` hooks
    ```sh
    just setup
    ```
