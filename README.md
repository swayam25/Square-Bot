<div align="center">

![Square Bot](./assets/square.png)

Advanced multipurpose discord bot for all your needs

</div>

## 🎬️ Preview

- **Moderation System**

    ![Moderation System](./assets/mod.gif)

- **Music Player**

    ![Music Player](./assets/music.gif)

- **Ticket System**

    ![Ticket System](./assets/ticket.gif)

## 🎯 Features

- Advanced moderation system
- Lots of utility & fun commands
- Advanced music system with control system
- Clean & informative help menu

## 🚀 Installation

1. Clone this repository
    ```sh
    git clone https://github.com/swayam25/Square-Bot square_bot
    cd square_bot
    ```

2. Rename the [`config.json.example`](./configs/config.json.example) file to `config.json`.

3. Configure the `config.json` file
    <details>

    <summary>Configuration</summary>

    - `owner_id` (`int`)
        - Owner's discord id
        - Gives access to all commands

    - `dev_ids` (`list[int]`)
        - Developer's discord ids
        - Gives access to developer commands
        - *This can be managed by `/dev list`, `/dev add` & `/dev remove` commands too*

    - `lockdown` (`bool`)
        - Lockdown status
        - If true, bot will not respond to any commands in any guild except owner's guilds
        - *This can be toggled by `/lockdown` command*

    - `owner_guild_ids` (`list[int]`)
        - List of guild ids
        - Developer commands will only work in these guilds

    - `system_ch_id` (`int`)
        - System channel id
        - Bot will send logs in this channel

    - `support_server_url` (`str`)
        - Support server url
        - Bot will use this url for support server

    - `discord_api_token` (`str`)
        - Discord api token
        - Bot will use this token to connect to discord

    - `lavalink` (`dict[str, Union[str, int, bool]]`)
        - `host` (`str`)
            - Lavalink host
        - `port` (`int`)
            - Lavalink port
        - `pass` (`str`)
            - Lavalink password
        - `secure` (`bool`)
            - Lavalink secure status

    - `spotify` (`dict[str, str]`)
        - `client_id` (`str`)
            - Spotify client id
        - `client_secret` (`str`)
            - Spotify client secret

    </details>

4. Set spotify credentials in [`config.json`](./configs/config.json) file.
    - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
    - Create a new application (*visit [Spotify Developer Docs](https://developer.spotify.com/documentation/web-api/tutorials/getting-started) for more details*).
    - Get the `client_id` and `client_secret` from the application settings.
    - Set the `client_id` and `client_secret` in the `config.json` file.


5. Set emojis in [`emoji.json`](./configs/emoji.json) file. If you want to use default emojis, you can change the `emoji_file_path` to `./configs/default_emoji.json` in [`emoji.py`](./utils/emoji.py) file.


5. Install dependencies
    ```sh
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

6. Start the bot
    ```sh
    python main.py
    ```
## 🌐 Production

1. Follow steps 1-4 from the [installation guide](#-installation). *Ignore if already done.*

2. Run docker container (*via `docker compose`*)
    ```sh
    docker compose up -d
    ```
