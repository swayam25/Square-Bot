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

    - `emoji` (`Literal["default", "custom"]`)
        - Emoji type.
        - `default` will use default emojis.
        - `custom` will use custom emojis defined in `.cache/emoji.json` (*requires setting up custom emojis*).
        - If you choose `custom`, make sure to define the emojis in the `.cache/emoji.json` file.
            1. To create custom emojis, upload a `.zip` file containing the emojis (*`.png` format*) using `/emoji upload` command.
                - There is a zip file of custom emojis that are used in this bot. Upload the [`emojis.zip`](./assets/emojis.zip) via `/emoji upload` command.
                - Emoji file names must match the attributes of `Emoji` class in [`emoji.py`](./utils/emoji.py). The [`emojis.zip`](./assets/emojis.zip) file already does this for you.
            2. Emojis are automatically stored in `.cache/emoji.json` file when you upload them via `/emoji upload` command.
                - You can manually run `/emoji sync` command to store bot's emojis in `.cache/emoji.json` file.
                - You can also manually create the `.cache/emoji.json` file with keys same as attributes in `Emoji` class in [`emoji.py`](./utils/emoji.py).
            3. Then set the `emoji` field to `custom`.

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
        - `error` (`str`)
            - Error color.

    - `[lavalink]`
        - `host` (`str`)
            - Lavalink host.
        - `port` (`int`)
            - Lavalink port.
        - `password` (`str`)
            - Lavalink password.
        - `secure` (`bool`)
            - Lavalink secure status

    </details>

3. Start the bot.
    ```sh
    uv run main.py
    ```

> [!IMPORTANT]
> Make sure to have [uv](https://docs.astral.sh/uv) installed on your system to run the bot.
> Know more about installing uv [here](https://docs.astral.sh/uv/getting-started/installation/).

## 🚀 Production

1. Follow steps 1 & 2 from the [installation guide](#-installation). *Ignore if already done.*

2. Run docker container (*via `docker compose`*)
    ```sh
    docker compose up -d
    ```

## ❤️ Contributing

- Things to keep in mind
    - Follow our commit message convention.
    - Write meaningful commit messages.
    - Keep the code clean and readable.
    - Make sure the bot is working as expected.

- Code Formatting
    - Run `ruff format` before committing your changes or use [`Ruff`](https://docs.astral.sh/ruff/editors) extension in your code editor.
    - Make sure to commit error free code. Run `ruff check` to check for any errors.
