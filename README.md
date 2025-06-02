<div align="center">

![Square Bot](./assets/banner.png)

Advanced multipurpose discord bot for all your needs.

</div>

## 🎯 Features

- Advanced moderation system.
- Lots of utility & fun commands.
- Advanced music system with support for YouTube, Spotify and SoundCloud.
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
        - `custom` will use custom emojis defined in `./.cache/emoji.json` (*requires setting up custom emojis*).
        - If you choose `custom`, make sure to define the emojis in the `./.cache/emoji.json` file.
            - To create custom emojis, upload a `.zip` file contaning the emojis (*`.png` format*) using `/emoji upload` command.
            - Emoji file names must match the attributes of `Emoji` class in [`emoji.py`](./utils/emoji.py).
            - Then run `/emoji sync` command to sync the emojis. (*This creates `./.cache/emoji.json` file from bot's emojis*).
            - You can also manually create the `./.cache/emoji.json` file with the same structure as `Emoji` class in [`emoji.py`](./utils/emoji.py).
            - Then set the `emoji` field to `custom`.

    - `bot-token` (`str`)
        - Discord api token.
        - Bot will use this token to connect to discord.

    - `database-url` (`str`)
        - Database url.
        - Bot will use this url to connect to the database.
        - Postgres database is supported.
        - Example: `asyncpg://user:password@localhost:5432/square`.
            - If you connection string starts with `postgresql://`, replace it with `asyncpg://`.
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

    - `[spotify]`
        - `client_id` (`str`)
            - Spotify client id
        - `client_secret` (`str`)
            - Spotify client secret

    </details>

3. Set spotify credentials in `config.toml` file.
    - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
    - Create a new application (*visit [Spotify Developer Docs](https://developer.spotify.com/documentation/web-api/tutorials/getting-started) for more details*).
    - Get the `client_id` and `client_secret` from the application settings.
    - Set the `client_id` and `client_secret` in the `config.toml` file.

4. Start the bot.
    ```sh
    uv run main.py
    ```

> [!IMPORTANT]
> Make sure to have [uv](https://docs.astral.sh/uv) installed on your system to run the bot.
> Know more about installing uv [here](https://docs.astral.sh/uv/getting-started/installation/).

## 🚀 Production

1. Follow steps 1-3 from the [installation guide](#-installation). *Ignore if already done.*

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
