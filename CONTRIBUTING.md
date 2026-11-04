# 🤝 Contributing

Thanks for wanting to help out! Whether it's a bug fix, a new feature, or a docs tweak, here's what you need to get a local copy running and how we like changes to land.

## 💫 Prerequisites

Everything in the [README's prerequisites](./README.md#-prerequisites), plus a couple of things only needed for development:

| Tool                                                                                                                                    | Version | Purpose                                           |
| --------------------------------------------------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------- |
| [![Python](https://img.shields.io/badge/Python-%233776AB?style=for-the-badge&logo=python&logoColor=%23FFFFFF)](https://www.python.org/) | 3.14+   | The programming language used to develop the bot. |
| [![UV](https://img.shields.io/badge/UV-%23DE5FE9?style=for-the-badge&logo=uv&logoColor=%23FFFFFF)](https://docs.astral.sh/uv/)          | 0.13+   | A modern Python package manager for development.  |

## 🛸 Local Development

1. Follow the first step of the [production setup](./README.md#-production) - clone the repo.

2. Install the dependencies, set up pre-commit hooks, and create your `config.toml` file

    ```sh
    just init
    ```

> [!TIP]
> Check [configuration](./README.md#-configuration) section for details on the configuration keys.

3. Start the local docker services

    ```sh
    just up --dev
    ```

4. Run the bot

    ```sh
    just dev
    ```

    > `just dev` auto-starts services if they aren't already running, so you can skip step 3 and run it directly. It also logs at `DEBUG`.

5. Stop it when done
    ```sh
    just down --dev
    ```

## 🗂️ Project Layout

```
src/square/
├── __main__.py        Entry point: `uv run square` or `python -m square`
├── bot.py             Startup: banner, database, cogs, shutdown
├── log.py             Logging setup (console, optional file)
├── core/              Shared by every cog: Client, Cog base class, DesignerView
├── db/                Tortoise models and database functions
├── music/             The music engine (players, queues, request channels)
├── utils/             Shared helpers: config, emojis, checks, server logs, invites
└── cogs/              One folder per cog
    ├── moderation/    __init__.py (the cog) + purge.py, roles.py
    ├── music/         __init__.py (the cog) + listeners.py, eq.py
    └── …
```

**Adding a cog**: create `src/square/cogs/<name>/__init__.py` with a `setup(client)` function. It's loaded automatically. Give the cog its help category through class keywords:

```py
from square.core.cog import Cog
from square.utils.emoji import emoji


class Voice(Cog, name="Voice", description="Move, mute and manage voice members.", emoji=emoji.voice, order=3): ...


def setup(client):
    client.add_cog(Voice(client))
```

`name` and `description` are py-cord's own. `emoji` and `order` place the cog in `/help`. A cog without `emoji` stays out of the menu, and `dev_only=True` shows it only to developers.

**Settings**: a cog adds a page to the `/settings` panel by subclassing `SettingsPage` (see `cogs/automod/settings.py`) and listing it in `settings_pages = (MyPage,)`. Read values from `square.db.cache` and save through the `db.funcs` setters, which update the database and the cache together.

**Keep state outside `cogs/`**: `/reload-cogs` reloads every module inside a cog folder, so anything that must survive a reload (caches, players) belongs in `music/`, `utils/` or `db/`.

**Big cogs**: split them into mixin classes in their own files (see `moderation/purge.py`) and list them as bases of the cog class. py-cord collects commands and listeners from every base, so it stays one cog and one help category.

## 📜 Logging

Use the standard `logging` module, never `print`:

```py
import logging

log = logging.getLogger(__name__)
log.info("Node %s connected", node.id)
```

Ruff blocks `print()` and Rich's `Console` outside `log.py`. Pass values as arguments (`%s`) instead of f-strings, so muted levels cost nothing.

## 🍀 Making a Pull Request

1. Fork the repository and clone your fork.
2. Follow [Local Development](#-local-development) above to get it running.
3. Create a branch for your change, commit your work, and open a pull request.

## 📋 Guidelines

- **Commits**: Write clear, meaningful messages that describe *what* changed and *why*, and follow the style used in the project's history.
- **Code quality**: Keep the code clean, readable, and consistent with the surrounding style. The `pre-commit` hooks run ruff on every commit, or run them yourself with `just check`.
- **Testing**: Run the bot locally and confirm your change works as expected before opening a PR.
