<div align="center">

![Square Bot](./assets/banner.png)

Advanced multipurpose discord bot for all your needs.

</div>

## 🎯 Features

- Advanced moderation system.
- Lots of utility & fun commands.
- Advanced music system with support for various sources (*depends on your Lavalink server*).
- Clean & informative help menu.

## 🚩 Installation

1. Clone this repository
    ```sh
    git clone https://github.com/swayam25/Square-Bot square
    cd square
    ```

2. Create `config.toml` from `example.config.toml` and fill in the required values.
    <details>

    <summary>Configuration</summary>

    - `owner-id` (`int`)
        - Owner's discord id.
        - Gives access to all commands.

    - `owner-guild-ids` (`list[int]`)
        - List of guild ids.
        - Developer commands will only work in these guilds.

    - `system-channel-id` (`int`)
        - System channel id.
        - Bot will send logs in this channel.

    - `support-server-url` (`str`)
        - Support server url.
        - Bot will use this url for support server.

    - `bot-token` (`str`)
        - Discord api token.
        - Bot will use this token to connect to discord.

    - `database-url` (`str`)
        - Database url.
        - Bot will use this url to connect to the database.
        - Postgres database is supported.
        - Example: `asyncpg://user:password@db.host:5432/square`.
            - If your connection string starts with `postgresql://`, replace it with `asyncpg://`.
            - Services like Supabase provide a `postgresql://` connection string, remember to change it to `asyncpg://`.

    - `[colors]`
        - `theme` (`str`)
            - Theme color.
        - `green` (`str`)
            - Green color.
        - `red` (`str`)
            - Red color.
        - `orange` (`str`)
            - Orange color.

    - `[lavalink]`
        - `host` (`str`)
            - Lavalink host.
        - `port` (`int`)
            - Lavalink port.
        - `password` (`str`)
            - Lavalink password.
        - `region` (`str`)
            - Lavalink region.
        - `secure` (`bool`)
            - Lavalink secure status

    </details>

3. Start the bot.
    ```sh
    uv run main.py
    ```

> [!IMPORTANT]
> Make sure to have [uv](https://docs.astral.sh/uv) installed on your system to run the bot.
> Learn more about installing uv [here](https://docs.astral.sh/uv/getting-started/installation/).

## 🚀 Production

1. Follow steps 1 & 2 from the [installation guide](#-installation). *Ignore if already done.*

2. Run docker container (*via `docker compose`*)
    ```sh
    docker compose up -d
    ```

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

- Code Formatting
    - Run `ruff format` before committing your changes, or use [`Ruff`](https://docs.astral.sh/ruff/editors) extension in your code editor.
    - Ensure the bot is working as expected. Run `ruff check` to check for any errors.
