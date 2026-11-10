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
├── imaging/           Card image engine and its templates
├── music/             The music engine (players, queues, request channels)
├── utils/             Shared helpers: config, emojis, checks, server logs, invites
╰── cogs/              One folder per cog
    ├── moderation/    __init__.py (the cog) + purge.py, roles.py
    ├── music/         __init__.py (the cog) + listeners.py, eq.py
    ╰── …
```

**Cogs**: add `src/square/cogs/<name>/__init__.py` with a `setup(client)` function and it loads automatically. Class keywords place it in `/help`:

```py
class Voice(Cog, name="Voice", description="Move, mute and manage voice members.", emoji=emoji.voice, order=3): ...


def setup(client):
    client.add_cog(Voice(client))
```

A cog without `emoji` stays out of `/help`, and `dev_only=True` shows it to developers only. Split a big cog into mixin classes in their own files (see `moderation/purge.py`). It's still one cog.

**Settings**: subclass `SettingsPage` (see `cogs/automod/settings.py`) and list it in the cog's `settings_pages`. Read from `square.db.cache` and save through the `db.funcs` setters.

**State**: `/reload-cogs` reloads everything under `cogs/`, so caches and players belong in `music/`, `utils/` or `db/`.

**Emojis**: add an `Icon` line to `Emoji` in `utils/emoji.py` and a same-named `.png`/`.gif` to `emojis/`, then press **Sync** in `/emoji`. To change one, replace the file and sync.

**Images**: `square.imaging` draws cards with Pillow in the same design as the website. A template in `imaging/templates/` turns plain data into a layout built from `Kit` components (`ui.chip`, `ui.stat`, `ui.tile`, …), and `imaging.render` puts it on the card. Add sample data for it in `templates/__init__.py`, preview it with `uv run python -m square.imaging <template>`, and send it from a cog with `await imaging.render(template.build, data, filename="card.png")`.

- **Colors**: every color is Tailwind's (`mist` greys, `emerald-400`, `amber-400`, `red-400`) except the accent, which comes from `colors.theme` in `config.toml`, all in `imaging/theme.py`. The other `[colors]` keys are Discord's own green, red and orange, used by embeds and emojis so they look native next to Discord's UI. Images don't sit in Discord's UI, so they stay on Tailwind. Components pick their own color roles (a warning chip uses the warning color), so templates never hard-code colors. A translucent Tailwind fill like `bg-red-400/10` is flattened onto the surface with `theme.tint()`.
- **Type and shape**: text styles are Tailwind's sizes in `imaging/tokens.py` (`Type.SM` is `text-sm`), set in Saira for titles, Noto Sans for reading and JetBrains Mono for numbers, handles and eyebrow labels. Every family falls back to the rest of Noto (math letters, symbols, color emoji), so any Discord name draws. Radii are Tailwind's too (`Radius.XL2` is `rounded-2xl`), and spacing sticks to even Tailwind steps (8, 16, 24 px).
- **Icons**: `ui.chip(..., icon=...)` and `ui.icon()` draw emojis from `emojis/`, recolored to match the text next to them. Only the icon's shape is used, so the file's color doesn't matter. Pass the plain name (`console`, `dj`), and use a variant like `_white`, `_green` or `_red` only when no plain file exists (e.g. `user_add_white`). Brand logos keep their own colors with `tint=False`.

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
