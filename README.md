<div align="center">

![Square Bot](./assets/banner.png)

# Square Bot

Advanced multipurpose discord bot for all your needs.

[![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fswayam25%2FSquare-Bot%2Fmain%2Fpyproject.toml&style=for-the-badge&logo=python&logoColor=%23FFFFFF&labelColor=%233776AB&color=%23000000)](https://www.python.org/downloads)
[![Pycord Version](https://img.shields.io/badge/pycord-v2.7.1-%23000000?style=for-the-badge&logo=python&logoColor=%23FFFFFF&labelColor=%235865F2)](https://github.com/Pycord-Development/pycord)
[![GitHub Release](https://img.shields.io/github/v/release/swayam25/Square-Bot?style=for-the-badge&logo=github&logoColor=%23FFFFFF&labelColor=%230D1117&color=%23000000)](https://github.com/swayam25/Square-Bot/releases)
[![GitHub License](https://img.shields.io/github/license/swayam25/Square-Bot?style=for-the-badge&logo=gnu&logoColor=%23FFFFFF&labelColor=%23A32D2A&color=%23000000)](https://github.com/swayam25/Square-Bot/blob/main/LICENSE)

</div>

## 🎯 Features

- Advanced moderation system.
- Lots of utility & fun commands.
- Advanced music system with support for various sources (*depends on your Lavalink server*).
- Clean & informative help menu.
- Supports Discord Components v2.

## 💫 Prerequisites

### 🧰 Tools

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

3. Example `Caddyfile` configuration for a domain `example.com`
    ```Caddyfile
    example.com {
        reverse_proxy drizzle-gateway:8080
    }
    ```

> [!NOTE]
> If you don't have a domain, you can use `:80` to access the database panel via your server's IP address. However, this is not recommended for production use.
>
> Read [Caddy's documentation](https://caddyserver.com/docs/caddyfile) for more details.

4. Build the images and start everything
    ```sh
    just prod
    ```

5. Done! The bot should be up and running now. You can access the database panel at `http(s)://<your-domain-or-ip>/`.

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
> For development Caddy is by-default configured to run on port `80`
>
> ```Caddyfile
> :80 {
>     reverse_proxy drizzle-gateway:8080
> }
> ```
>
> This allows you to access the database panel via `http://localhost` without needing a domain or SSL certificate, which simplifies the development process.

## 🔑 Configuration

| Key                  | Type        | Description                                                                                                  |
| -------------------- | ----------- | ------------------------------------------------------------------------------------------------------------ |
| `owner-id`           | `int`       | The Discord ID of the bot owner.                                                                             |
| `owner-guild-ids`    | `list[int]` | A list of Discord IDs of the owner's guilds. Owner/Developer only commands are created only in these guilds. |
| `system-channel-id`  | `int`       | The Discord ID of the system channel where the bot will send startup, guild join/leave etc... messages.      |
| `support-server-url` | `str`       | The invite URL of the support server.                                                                        |
| `bot-token`          | `str`       | Discord Bot Token. Get this from developer portal.                                                           |
| `drizzle-password`   | `str`       | The password for Drizzle Studio Gateway. This is used to access the database panel.                          |
| `database-url`       | `str`       | The URL for the PostgreSQL database.                                                                         |
| `colors.theme`       | `str`       | The color theme for the bot's view containers.                                                               |
| `colors.green`       | `str`       | The color code for green color in view containers.                                                           |
| `colors.red`         | `str`       | The color code for red color in view containers.                                                             |
| `colors.orange`      | `str`       | The color code for orange color in view containers.                                                          |
| `lavalink.host`      | `str`       | The host of the Lavalink server.                                                                             |
| `lavalink.port`      | `int`       | The port of the Lavalink server.                                                                             |
| `lavalink.password`  | `str`       | The password for the Lavalink server.                                                                        |
| `lavalink.region`    | `str`       | The region of the Lavalink server.                                                                           |
| `lavalink.secure`    | `bool`      | Whether to use secure connection (wss) for Lavalink.                                                         |

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
