import asyncio
import datetime
import discord
import math
import os
import platform
import psutil
import sonolink
import sys
import time
import toml
import zipfile
from babel.dates import format_timedelta
from collections import defaultdict, deque
from core import Client
from core.view import DesignerView
from db.funcs.dev import add_dev, fetch_dev_ids, remove_dev
from db.funcs.guild import add_guild, remove_guild
from discord import ui
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from discord.ui import ActionRow
from io import BytesIO
from music.core import fetch_node_info
from typing import Literal
from utils import check, config, temp
from utils.emoji import Emoji, emoji, reload_emoji, update_emoji
from utils.helpers import fmt_memory
from utils.logger import cleanup_guild
from utils.term import Term


def _has_stats(node: sonolink.Node) -> bool:
    """Whether a node has reported real stats."""
    return bool(node.is_connected and node.stats is not None)


class GuildContainer(ui.Container):
    def __init__(self, guilds, page=1, items_per_page=10):
        super().__init__()
        total_pages = max(1, math.ceil(len(guilds) / items_per_page))
        start = (page - 1) * items_per_page
        end = start + items_per_page
        page_guilds = guilds[start:end]
        guilds_list = "\n".join(f"`{i + 1}.` **{g.name}**: `{g.id}`" for i, g in enumerate(page_guilds, start=start))
        self.add_item(ui.TextDisplay("## Guild List"))
        self.add_item(ui.TextDisplay(guilds_list or "No guilds found."))
        if len(guilds) > items_per_page:
            self.add_item(ui.Separator())
            self.add_item(ui.TextDisplay(f"-# Page {page} / {total_pages}"))


class GuildListView(DesignerView):
    def __init__(self, client: Client, ctx: discord.ApplicationContext, page: int = 1):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.client = client
        self.page = page
        self.items_per_page = 10
        self.build()

    def build(self) -> None:
        self.clear_items()
        guilds = self.client.guilds
        self.add_item(GuildContainer(guilds, page=self.page, items_per_page=self.items_per_page))
        row = ActionRow()
        for btn_emoji, callback in [
            (emoji.start_white, "start"),
            (emoji.previous_white, "previous"),
            (emoji.next_white, "next"),
            (emoji.end_white, "end"),
        ]:
            btn = ui.Button(emoji=btn_emoji, style=discord.ButtonStyle.grey)
            btn.callback = lambda i, action=callback: self.interaction_callback(i, action)
            row.add_item(btn)
        self.add_item(row)

    async def interaction_callback(self, interaction: discord.Interaction, action: str):
        guilds = self.client.guilds
        total_pages = math.ceil(len(guilds) / self.items_per_page)
        if action == "start":
            self.page = 1
        elif action == "previous":
            self.page = total_pages if self.page <= 1 else self.page - 1
        elif action == "next":
            self.page = 1 if self.page >= total_pages else self.page + 1
        elif action == "end":
            self.page = total_pages
        self.build()
        await interaction.edit(view=self)


class StatsView(DesignerView):
    """A terminal-style report of bot, host & lavalink node stats, split across two pages."""

    process = psutil.Process()

    BAR_WIDTH = 10
    CHART_HEIGHT = 4
    REPORT_LIMIT = 3900
    HISTORY_LEN = 40
    AUTO_REFRESH_INTERVAL = 2
    VIEW_TIMEOUT = 120

    def __init__(self, client: Client, ctx: discord.ApplicationContext):
        super().__init__(ctx=ctx, check_author_interaction=True, timeout=self.VIEW_TIMEOUT)
        self.client = client
        self.history: defaultdict[str, deque[float]] = defaultdict(lambda: deque(maxlen=self.HISTORY_LEN))
        self.page: Literal["main", "lavalink"] = "main"
        self.auto = False
        self.auto_task: asyncio.Task | None = None
        self.build_lock = asyncio.Lock()

    def _track(self, key: str, value: float) -> list[float]:
        """Appends a sample and returns the series so far."""
        self.history[key].append(value)
        return list(self.history[key])

    def _bar(self, percent: float) -> str:
        """Renders a percentage as a fixed-width ASCII meter, e.g. `[####------]  42.1%`."""
        percent = min(max(percent, 0.0), 100.0)
        filled = int(round(self.BAR_WIDTH * percent / 100))
        return f"[{'#' * filled}{'-' * (self.BAR_WIDTH - filled)}] {percent:5.1f}%"

    def _axis(self, low: float, high: float) -> list[str]:
        """Formats the y-axis labels, top row first."""
        values = [high - (high - low) * r / self.CHART_HEIGHT for r in range(self.CHART_HEIGHT + 1)]
        labels = [f"{v:.0f}" for v in values]
        for decimals in range(1, 4):
            if len(set(labels)) == len(labels):
                break
            labels = [f"{v:.{decimals}f}" for v in values]
        return labels

    def _chart(self, title: str, series: list[float]) -> list[str]:
        """Plots a series as a line chart; renders only while auto-refresh is running."""
        caption = f"     last {len(series)} samples"
        if not self.auto or len(series) < 2:
            return []

        low, high = min(series), max(series)
        if high - low < 1e-9:
            return [title, f"  {Term.num(low)} ┼{'─' * len(series)}", caption, ""]

        def row_of(value: float) -> int:
            return round((value - low) / (high - low) * self.CHART_HEIGHT)

        labels = self._axis(low, high)
        label_width = max(len(label) for label in labels)
        grid = [[" "] * len(series) for _ in range(self.CHART_HEIGHT + 1)]

        for x in range(len(series) - 1):
            start, end = row_of(series[x]), row_of(series[x + 1])
            if start == end:
                grid[self.CHART_HEIGHT - start][x] = "─"
            else:
                grid[self.CHART_HEIGHT - end][x] = "╰" if start > end else "╭"
                grid[self.CHART_HEIGHT - start][x] = "╮" if start > end else "╯"
                for y in range(min(start, end) + 1, max(start, end)):
                    grid[self.CHART_HEIGHT - y][x] = "│"
        grid[self.CHART_HEIGHT - row_of(series[-1])][-1] = "─"

        origin = self.CHART_HEIGHT - row_of(series[0])
        lines = [
            f"  {label.rjust(label_width)} {'┼' if r == origin else '┤'}{''.join(row)}".rstrip()
            for r, (label, row) in enumerate(zip(labels, grid, strict=True))
        ]
        return [title, *lines, caption, ""]

    async def build(self) -> None:
        # Serialize rebuilds and keep the clear/add mutation free of awaits: a concurrent
        # build (auto-refresh tick vs button click) would otherwise interleave and leave the
        # view empty or with duplicated components.
        async with self.build_lock:
            sections, omitted = await (self._main_sections() if self.page == "main" else self._lavalink_sections())

            self.clear_items()
            container = ui.Container()
            for section in sections:
                container.add_item(ui.TextDisplay(Term.fence(section)))
            if omitted:
                container.add_item(
                    ui.TextDisplay(f"-# {omitted} node section{'s' if omitted > 1 else ''} omitted: report too long.")
                )
            container.add_item(
                ui.TextDisplay(f"-# Updated {discord.utils.format_dt(datetime.datetime.now(datetime.UTC), 'R')}")
            )
            self.add_item(container)

            nav = ui.Button(
                emoji=emoji.music_white if self.page == "main" else emoji.previous_white,
                label="Lavalink" if self.page == "main" else "Back",
                style=discord.ButtonStyle.grey,
                custom_id="stats_nav_btn",
            )
            nav.callback = self._switch_page
            refresh = ui.Button(
                emoji=emoji.reload_white,
                label="Refresh",
                style=discord.ButtonStyle.grey,
                custom_id="refresh_stats_btn",
            )
            refresh.callback = self._manual_refresh
            auto = ui.Button(
                emoji=emoji.pause_white if self.auto else emoji.play_white,
                label="Stop Auto Refresh" if self.auto else "Auto Refresh",
                style=discord.ButtonStyle.grey,
                custom_id="auto_stats_btn",
            )
            auto.callback = self._toggle_auto
            self.add_item(ui.ActionRow(nav, refresh, auto))

    async def _manual_refresh(self, interaction: discord.Interaction) -> None:
        self.disable_all_items()
        if btn := self.get_item("refresh_stats_btn"):
            btn.emoji = emoji.loading_white
            btn.label = "Refreshing..."
        await interaction.edit(view=self)
        await self.build()
        await interaction.edit(view=self)

    async def _switch_page(self, interaction: discord.Interaction) -> None:
        self.page = "lavalink" if self.page == "main" else "main"
        self.disable_all_items()
        if btn := self.get_item("stats_nav_btn"):
            btn.emoji = emoji.loading_white
        await interaction.edit(view=self)
        await self.build()
        await interaction.edit(view=self)

    async def _toggle_auto(self, interaction: discord.Interaction) -> None:
        self.auto = not self.auto
        self._cancel_auto()
        if self.auto:
            self.history.clear()
        self.disable_all_items()
        if btn := self.get_item("auto_stats_btn"):
            btn.emoji = emoji.loading_white
        await interaction.edit(view=self)
        await self.build()
        await interaction.edit(view=self)
        if self.auto:
            self.auto_task = asyncio.create_task(self._auto_loop(interaction.message))

    def _cancel_auto(self) -> None:
        if self.auto_task:
            self.auto_task.cancel()
            self.auto_task = None

    async def _auto_loop(self, message: discord.Message) -> None:
        try:
            while self.auto:
                await asyncio.sleep(self.AUTO_REFRESH_INTERVAL)
                await self.build()
                await message.edit(view=self)
        except asyncio.CancelledError:
            pass
        except discord.HTTPException:
            self.auto = False

    async def on_timeout(self) -> None:
        self.auto = False
        self._cancel_auto()
        await super().on_timeout()

    async def _main_sections(self) -> tuple[list[list[str]], int]:
        self.process.cpu_percent()  # prime: cpu_percent measures since the previous call

        host_cpu = await asyncio.to_thread(psutil.cpu_percent, 0.1)
        return [self._bot_block(), self._runtime_block(), self._host_block(host_cpu)], 0

    async def _lavalink_sections(self) -> tuple[list[list[str]], int]:
        nodes = self.client.sonolink.nodes
        sections = [self._nodes_block(nodes)]
        sections += await asyncio.gather(*(self._node_block(i, n) for i, n in enumerate(nodes, start=1)))

        omitted = 0
        while sum(len(Term.fence(s)) for s in sections) > self.REPORT_LIMIT and len(sections) > 1:
            sections, omitted = sections[:-1], omitted + 1
        return sections, omitted

    def _bot_block(self) -> list[str]:
        uptime = datetime.timedelta(seconds=int(time.time() - self.process.create_time()))
        latency = self.client.latency * 1000
        rows = [
            ("Latency", f"{round(latency)} ms"),
            ("Uptime", format_timedelta(uptime, locale="en")),
            ("Shards", f"{self.client.shard_count or 1}"),
            ("Commands", f"{len(self.client.application_commands):,}"),
            ("Guilds", f"{len(self.client.guilds):,}"),
            ("Members", f"{sum(1 for _ in self.client.get_all_members()):,}"),
            ("Channels", f"{sum(1 for _ in self.client.get_all_channels()):,}"),
            ("Voice", f"{len(self.client.voice_clients):,}"),
        ]
        return ["BOT", *Term.kv(rows), "", *self._chart("Latency (ms)", self._track("latency", latency))]

    def _runtime_block(self) -> list[str]:
        with open("pyproject.toml") as f:
            version = toml.load(f)["project"]["version"]
        rss = self.process.memory_info().rss
        rows = [
            ("Square", f"v{version}"),
            ("Python", f"v{platform.python_version()}"),
            ("Pycord", f"v{discord.__version__}"),
            ("Sonolink", f"v{sonolink.__version__}"),
            ("PID", f"{self.process.pid}"),
            ("Threads", f"{self.process.num_threads():,}"),
            ("RSS", fmt_memory(rss)),
            ("CPU", f"{self.process.cpu_percent():.1f}%"),
        ]
        return ["RUNTIME", *Term.kv(rows), "", *self._chart("RSS (MB)", self._track("rss", rss / 1024 / 1024))]

    def _host_block(self, host_cpu: float) -> list[str]:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        freq = psutil.cpu_freq()
        cores = psutil.cpu_count(logical=False) or 0
        threads = psutil.cpu_count() or 0
        grid = Term.grid(
            ["RESOURCE", "USED", "TOTAL", "LOAD"],
            [
                ["Memory", fmt_memory(mem.used), fmt_memory(mem.total), self._bar(mem.percent)],
                ["Storage", fmt_memory(disk.used), fmt_memory(disk.total), self._bar(disk.percent)],
                ["CPU", f"{threads} thr", f"{cores} cores", self._bar(host_cpu)],
            ],
        )
        rows = [
            ("System", f"{platform.system()} {platform.release()}"),
            ("Machine", platform.machine()),
            ("CPU Clock", f"{round(freq.current):,} MHz" if freq else "unknown"),
        ]
        return [
            "HOST",
            *Term.kv(rows, cols=1),
            "",
            *grid,
            "",
            *self._chart("CPU (%)", self._track("host_cpu", host_cpu)),
            *self._chart("Memory (%)", self._track("host_mem", mem.percent)),
        ]

    def _nodes_block(self, nodes: list[sonolink.Node]) -> list[str]:
        if not nodes:
            return ["LAVALINK", "  No nodes are configured."]
        rows = []
        for i, node in enumerate(nodes, start=1):
            stats = _has_stats(node)
            rows.append(
                [
                    f"{i}",
                    node.id,
                    "ONLINE" if node.is_connected else "OFFLINE",
                    f"{node.stats.players}" if stats else "-",
                    f"{node.stats.playing_players}" if stats else "-",
                ]
            )
        online_count = sum(1 for n in nodes if n.is_connected)
        return [
            f"LAVALINK • {online_count}/{len(nodes)} online",
            *Term.grid(["#", "NODE", "STATE", "PLAYERS", "PLAYING"], rows),
        ]

    async def _node_block(self, index: int, node: sonolink.Node) -> list[str]:
        title = f"NODE {index} • {node.id}"
        if not node.is_connected:
            return [title, *Term.kv([("State", "OFFLINE")], cols=1)]

        info, node_rest = await fetch_node_info(node)
        rows = [
            ("State", "ONLINE"),
            ("Version", f"v{info.version.semver}" if info else "unknown"),
            ("Rest", node_rest),
        ]
        if info:
            rows += [
                ("JVM", f"v{info.jvm}"),
                ("Lavaplayer", f"v{info.lavaplayer}"),
                ("Sources", ", ".join(info.source_managers) or "none"),
            ]
            if info.plugins:
                rows += [("Plugins" if i == 0 else "", f"{p.name} v{p.version}") for i, p in enumerate(info.plugins)]
            else:
                rows.append(("Plugins", "none"))
        if not _has_stats(node):
            return [title, *Term.kv(rows, cols=1), "", "  Awaiting first stats frame."]

        stats = node.stats
        rows += [
            ("Uptime", format_timedelta(datetime.timedelta(milliseconds=stats.uptime), locale="en")),
            ("Players", f"{stats.players:,}"),
            ("Playing", f"{stats.playing_players:,}"),
            ("Memory", f"{fmt_memory(stats.memory.used)} / {fmt_memory(stats.memory.allocated)}"),
        ]
        allocated = stats.memory.allocated or 1
        return [
            title,
            *Term.kv(rows, cols=1),
            "",
            f"  {'Memory'.ljust(8)} {self._bar(stats.memory.used / allocated * 100)}",
            f"  {'CPU Sys'.ljust(8)} {self._bar(stats.cpu.system_load * 100)}",
            f"  {'CPU Lava'.ljust(8)} {self._bar(stats.cpu.lavalink_load * 100)}",
        ]


class SyncEmojiView(DesignerView):
    def __init__(self, client: Client, ctx: discord.ApplicationContext):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.client = client

    async def build(self) -> None:
        self.clear_items()
        emojis: list[discord.AppEmoji] = await self.client.fetch_emojis()
        emoji_dict: dict = {}

        for app_emoji in emojis:
            if app_emoji.animated:
                emoji_dict[app_emoji.name] = f"<a:{app_emoji.name}:{app_emoji.id}>"
            else:
                emoji_dict[app_emoji.name] = f"<:{app_emoji.name}:{app_emoji.id}>"
        resp: dict = Emoji.create_custom_emoji_config(emoji_dict)
        reload_emoji()
        default_emojis_used: list[str] = resp.get("default_emojis_used", [])
        extra_keys_ignored: list[str] = resp.get("extra_keys_ignored", [])

        color = config.color.orange if extra_keys_ignored else None
        view_items = [
            ui.TextDisplay(f"## Synced {len(emojis)} emojis"),
            ui.TextDisplay(
                f"{emoji.bullet} **Total Emojis**: `{len(emojis)}`\n"
                f"{emoji.bullet} **Default Emojis**: `{len(default_emojis_used)}`\n"
                f"{emoji.bullet} **Extra Emojis**: `{len(extra_keys_ignored)}`\n"
            ),
        ]
        if default_emojis_used:
            view_items.extend(
                [
                    ui.Separator(),
                    ui.TextDisplay("### Default Emojis Used"),
                    ui.TextDisplay("".join(f"{getattr(emoji, i)} `{i}`\n" for i in default_emojis_used)),
                ]
            )
        if extra_keys_ignored:
            view_items.extend(
                [
                    ui.Separator(),
                    ui.TextDisplay("### Extra Emojis"),
                    ui.TextDisplay("".join(f"{emoji_dict.get(i, emoji.bullet)} `{i}`\n" for i in extra_keys_ignored)),
                ]
            )
            extra_btn = ui.Button(
                emoji=emoji.bin_white,
                label="Delete Extra Emojis",
                style=discord.ButtonStyle.grey,
                custom_id="delete_extra_emojis_btn",
            )

            async def extra_btn_callback(i: discord.Interaction):
                await self.delete_extra_emojis_callback(i, [emoji_dict.get(e) for e in extra_keys_ignored])

            extra_btn.callback = extra_btn_callback
            self.add_item(ui.Container(*view_items, **({"color": color} if color else {})))
            self.add_item(ui.ActionRow(extra_btn))
            return  # Early return to avoid re-adding view_items, button row must be at the end.
        self.add_item(ui.Container(*view_items, **({"color": color} if color else {})))

    async def delete_extra_emojis_callback(self, interaction: discord.Interaction, emojis: list[str]):
        """Deletes extra emojis."""
        btn = self.get_item("delete_extra_emojis_btn")
        btn.label = "Deleting..."
        btn.emoji = emoji.loading_white
        self.disable_all_items()
        await interaction.edit(view=self)
        for e in emojis:
            obj = e.strip("<>").split(":")
            id = int(obj[-1]) if len(obj) > 1 else None
            if id:
                await self.client.delete_emoji(discord.Object(id=id))
        await self.build()
        await interaction.edit(view=self)


class Devs(commands.Cog):
    def __init__(self, client: Client):
        self.client = client

    # On start
    @commands.Cog.listener("on_ready")
    async def when_bot_gets_ready(self):
        start_log_ch = await self.client.fetch_channel(config.system_channel_id)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.success} Logged in as **{self.client.user}** with ID `{self.client.user.id}`"),
                color=config.color.green,
            )
        )
        await start_log_ch.send(view=view)

    # On guild joined
    @commands.Cog.listener("on_guild_join")
    async def when_guild_joined(self, guild: discord.Guild):
        await add_guild(guild.id)
        join_log_ch = await self.client.fetch_channel(config.system_channel_id)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay("## Someone Added Me!"),
                ui.TextDisplay(
                    f"{emoji.server} **Name**: {guild.name}\n"
                    f"{emoji.id} **ID**: `{guild.id}`\n"
                    f"{emoji.members} **Total Members**: `{guild.member_count} ({len([m for m in guild.members if not m.bot])} Humans | {len([m for m in guild.members if m.bot])} Bots)`"
                ),
            )
        )
        await join_log_ch.send(view=view)

    # On guild leave
    @commands.Cog.listener("on_guild_remove")
    async def when_removed_from_guild(self, guild: discord.Guild):
        await remove_guild(guild.id)
        await cleanup_guild(guild.id, {c.id for c in guild.channels})
        leave_log_ch = await self.client.fetch_channel(config.system_channel_id)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay("## Someone Removed Me!"),
                ui.TextDisplay(
                    f"{emoji.server_red} **Name**: {guild.name}\n"
                    f"{emoji.id_red} **ID**: `{guild.id}`\n"
                    f"{emoji.members_red} **Total Members**: `{guild.member_count} ({len([m for m in guild.members if not m.bot])} Humans | {len([m for m in guild.members if m.bot])} Bots)`"
                ),
                color=config.color.red,
            )
        )
        await leave_log_ch.send(view=view)

    # Dev slash cmd group
    dev = SlashCommandGroup(guild_ids=config.owner_guild_ids, name="dev", description="Developer related commands.")

    # Add dev
    @dev.command(name="add")
    @check.is_owner()
    @option("user", description="Mention the user whom you want to add to dev")
    async def add_dev(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Adds a bot dev."""
        await add_dev(user.id)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.success} Added {user.mention} to dev."),
                color=config.color.green,
            ),
        )
        await ctx.respond(view=view)

    # Remove dev
    @dev.command(name="remove")
    @check.is_owner()
    @option("user", description="Mention the user whom you want to remove from dev")
    async def remove_dev(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Removes a bot dev."""
        await remove_dev(user.id)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.success} Removed {user.mention} from dev"),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    # List devs
    @dev.command(name="list")
    @check.is_owner()
    async def list_devs(self, ctx: discord.ApplicationContext):
        """Shows bot devs."""
        num = 0
        devs_list = ""
        dev_ids = await fetch_dev_ids()
        for ids in dev_ids:
            num += 1
            dev_mention = f"<@{ids}>"
            devs_list += f"`{num}.` {dev_mention}\n"
        if devs_list:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay("## Dev List"),
                    ui.TextDisplay(devs_list),
                )
            )
        else:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} No devs found."),
                    color=config.color.red,
                )
            )
        await ctx.respond(view=view)

    # Restart
    @slash_command(guild_ids=config.owner_guild_ids, name="restart")
    @check.is_dev()
    async def restart(self, ctx: discord.ApplicationContext):
        """Restarts the bot."""
        await self.client.change_presence(
            status=discord.Status.idle,
            activity=discord.CustomActivity(name="Restarting..."),
        )
        view = DesignerView(ui.Container(ui.TextDisplay(f"{emoji.loading} Restarting...")))
        msg = await ctx.respond(view=view)
        temp.set("restart_msg", {"channel_id": msg.channel.id, "id": (await msg.original_message()).id})
        await self.client.wait_until_ready()
        await self.client.close()
        os.system("clear")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # Reload cogs
    @slash_command(guild_ids=config.owner_guild_ids, name="reload-cogs")
    @check.is_dev()
    async def reload_cogs(self, ctx: discord.ApplicationContext):
        """Reloads the bot cogs."""
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.reload} Reloaded Cogs"),
            )
        )
        await ctx.respond(view=view, ephemeral=True, delete_after=2)
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                self.client.reload_extension(f"cogs.{filename[:-3]}")

    # Shutdown
    @slash_command(guild_ids=config.owner_guild_ids, name="shutdown")
    @check.is_owner()
    async def shutdown(self, ctx: discord.ApplicationContext):
        """Shutdowns the bot."""
        await self.client.change_presence(
            status=discord.Status.dnd,
            activity=None,
        )
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.shutdown} Bot is now shutdown."),
                color=config.color.red,
            )
        )
        await ctx.respond(view=view)
        await self.client.wait_until_ready()
        await self.client.close()

    # Set status
    @slash_command(guild_ids=config.owner_guild_ids, name="status")
    @check.is_dev()
    @option("status", description="Set the bot status", choices=["Online", "Idle", "DND", "Invisible"])
    @option("activity", description="Set the bot activity", max_length=128)
    async def set_status(self, ctx: discord.ApplicationContext, status: str, activity: str = None):
        """Sets the bot status."""
        await self.client.change_presence(
            status=discord.Status[status.lower()],
            activity=discord.CustomActivity(name=activity) if activity else self.client.activity,
        )
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(
                    f"{emoji.success} Status updated to `{status}`\n" + (f"```\n{activity}\n```" if activity else "")
                ),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    # Stats
    @slash_command(guild_ids=config.owner_guild_ids, name="stats")
    @check.is_dev()
    async def stats(self, ctx: discord.ApplicationContext):
        """Shows bot, host & lavalink node stats."""
        await ctx.defer()
        view = StatsView(self.client, ctx)
        await view.build()
        await ctx.respond(view=view)

    # Guild slash cmd group
    guild = SlashCommandGroup(guild_ids=config.owner_guild_ids, name="guild", description="Guild related commands.")

    # List guild
    @guild.command(name="list")
    @check.is_owner()
    async def list_guilds(self, ctx: discord.ApplicationContext):
        """Shows all guilds."""
        guild_list_view = None
        if len(self.client.guilds) > 10:
            guild_list_view = GuildListView(self.client, ctx)
        else:
            guilds = self.client.guilds
            container = GuildContainer(guilds)
            guild_list_view = DesignerView(container)
        await ctx.respond(view=guild_list_view)

    # Leave guild
    @guild.command(name="leave")
    @check.is_owner()
    @option(
        "guild",
        description="Enter the guild name",
        autocomplete=lambda self, ctx: [
            guild.name for guild in self.client.guilds if not any(guild.id == g for g in config.owner_guild_ids)
        ],
    )
    async def leave_guild(self, ctx: discord.ApplicationContext, guild: discord.Guild):
        """Leaves a guild."""
        if any(guild.id == g for g in config.owner_guild_ids):
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} I can't leave the owner guild."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await guild.leave()
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Left the guild **{guild.name}** with ID `{guild.id}`"),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    # Guild invite
    @guild.command(name="invite")
    @check.is_owner()
    @option(
        "guild",
        description="Enter the guild name",
        autocomplete=lambda self, ctx: [
            guild.name for guild in self.client.guilds if not any(guild.id == g for g in config.owner_guild_ids)
        ],
    )
    async def guild_inv(self, ctx: discord.ApplicationContext, guild: discord.Guild):
        """Creates an invite link for the guild."""
        if any(guild.id == g for g in config.owner_guild_ids):
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} I can't create an invite link for the owner guild"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            invite = await guild.text_channels[0].create_invite(max_age=0, max_uses=0)
            await ctx.respond(invite.url)

    # Emoji slash cmd group
    emoji = SlashCommandGroup(guild_ids=config.owner_guild_ids, name="emoji", description="Emoji related commands.")

    # Download app emojis
    @emoji.command(name="download")
    @check.is_dev()
    async def download_app_emojis(self, ctx: discord.ApplicationContext):
        """Downloads all emojis from the app."""
        await ctx.defer()
        emojis: list[discord.AppEmoji] = await self.client.fetch_emojis()
        if not emojis:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} No emojis found in the app."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for app_emoji in emojis:
                async with self.client.http._HTTPClient__session.get(app_emoji.url) as response:
                    if response.status == 200:
                        if app_emoji.animated:
                            zip_file.writestr(f"{app_emoji.name}.gif", await response.read())
                        else:
                            zip_file.writestr(f"{app_emoji.name}.png", await response.read())

        zip_buffer.seek(0)
        await ctx.respond(file=discord.File(fp=zip_buffer, filename="emojis.zip"))

    def emoji_prog_view(self, total: int, completed: int = 0) -> DesignerView:
        progress = (completed / total) * 100
        bar_length = 15
        filled_length = int(bar_length * completed // total)
        bar = f"{emoji.filled_bar * filled_length}{emoji.empty_bar * (bar_length - filled_length)}"
        return DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.loading} Uploading `{completed}/{total}` emojis.\n{bar} `{progress:.2f}%`"),
            )
        )

    async def _silent_sync(self) -> None:
        """Fetch current app emojis, write the config, and refresh the in-memory emoji singleton."""
        app_emojis: list[discord.AppEmoji] = await self.client.fetch_emojis()
        emoji_dict: dict = {
            e.name: (f"<a:{e.name}:{e.id}>" if e.animated else f"<:{e.name}:{e.id}>") for e in app_emojis
        }
        Emoji.create_custom_emoji_config(emoji_dict)
        reload_emoji()

    async def _sync_emoji_view(self, ctx: discord.ApplicationContext) -> SyncEmojiView:
        """Runs a full emoji sync and returns the summary view with the delete extra emojis button."""
        view = SyncEmojiView(self.client, ctx)
        await view.build()
        return view

    # Upload app emojis
    @emoji.command(name="upload")
    @check.is_dev()
    @option("file", description="Upload emojis zip file or single png or gif file.", type=discord.Attachment)
    async def upload_app_emojis(self, ctx: discord.ApplicationContext, file: discord.Attachment):
        """Uploads emojis to the app from a .zip file or single .png/.gif file."""
        await ctx.defer()
        if file.filename.endswith(".zip"):
            zip_buffer = BytesIO()
            await file.save(zip_buffer)
            zip_buffer.seek(0)
            with zipfile.ZipFile(zip_buffer, "r") as zip_file:
                namelist = zip_file.namelist()
                file_entries = [n for n in namelist if not n.endswith("/")]
                top_dirs = set()
                for n in namelist:
                    parts = n.split("/")
                    if len(parts) > 1 and parts[0]:
                        top_dirs.add(parts[0])
                if len(top_dirs) > 1:
                    view = DesignerView(
                        ui.Container(
                            ui.TextDisplay(f"{emoji.error} Zip file contains more than one top-level directory."),
                            color=config.color.red,
                        )
                    )
                    await ctx.respond(view=view, ephemeral=True)
                    return
                if len(top_dirs) == 1:
                    base_dir = list(top_dirs)[0]
                    emoji_files = [
                        f for f in file_entries if f.startswith(base_dir + "/") and f.endswith((".png", ".gif"))
                    ]
                else:
                    emoji_files = [f for f in file_entries if "/" not in f and f.endswith((".png", ".gif"))]
                if not emoji_files:
                    view = DesignerView(
                        ui.Container(
                            ui.TextDisplay(f"{emoji.error} No `.png` or `.gif` emoji files found in the zip."),
                            color=config.color.red,
                        )
                    )
                    await ctx.respond(view=view, ephemeral=True)
                    return
                emoji_images: dict[str, bytes] = {}
                for emoji_path in emoji_files:
                    _emoji = emoji_path.split("/")[-1][:-4]
                    if len(_emoji) > 32:
                        view = DesignerView(
                            ui.Container(
                                ui.TextDisplay(f"{emoji.error} Emoji name `{_emoji}` is too long (max 32 characters)."),
                                color=config.color.red,
                            )
                        )
                        await ctx.respond(view=view, ephemeral=True)
                        return
                    emoji_images[_emoji] = zip_file.read(emoji_path)
            zip_buffer.close()

            view = self.emoji_prog_view(len(emoji_images))
            msg = await ctx.respond(view=view)

            existing = {e.name: e for e in await self.client.fetch_emojis()}
            semaphore = asyncio.Semaphore(5)
            completed = 0
            failed: dict[str, str] = {}

            async def upload_one(name: str, image: bytes) -> None:
                nonlocal completed
                async with semaphore:
                    try:
                        try:
                            uploaded = await self.client.create_emoji(name=name, image=image)
                        except Exception:
                            if name not in existing:
                                raise
                            await self.client.delete_emoji(existing[name])
                            uploaded = await self.client.create_emoji(name=name, image=image)
                        # Patch the singleton immediately so progress edits never render a deleted emoji ID
                        update_emoji(
                            uploaded.name,
                            f"<a:{uploaded.name}:{uploaded.id}>"
                            if uploaded.animated
                            else f"<:{uploaded.name}:{uploaded.id}>",
                        )
                    except Exception as e:
                        failed[name] = str(e)
                    finally:
                        completed += 1

            uploads = asyncio.gather(*(upload_one(name, image) for name, image in emoji_images.items()))
            last_shown = 0
            while not uploads.done():
                if completed != last_shown:
                    last_shown = completed
                    await msg.edit(view=self.emoji_prog_view(len(emoji_images), completed))
                await asyncio.sleep(1)
            await uploads

            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.loading} Uploaded {len(emoji_images) - len(failed)} emojis. *Syncing...*"),
                )
            )
            await msg.edit(view=view)
            await msg.edit(view=await self._sync_emoji_view(ctx))
            if failed:
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay("### Failed Emojis"),
                        ui.TextDisplay(
                            "".join(f"{emoji.bullet_red} `{name}`: {err}\n" for name, err in failed.items())
                        ),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)
        elif file.filename.endswith((".png", ".gif")):
            # Handle single PNG or GIF file upload
            if len(file.filename[:-4]) > 32:
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay(
                            f"{emoji.error} Emoji name `{file.filename[:-4]}` is too long (max 32 characters)."
                        ),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)
                return
            png_buffer = BytesIO()
            await file.save(png_buffer)
            png_buffer.seek(0)
            try:
                uploaded_emoji = await self.client.create_emoji(name=file.filename[:-4], image=png_buffer.read())
                emoji_md = (
                    f"<a:{uploaded_emoji.name}:{uploaded_emoji.id}>"
                    if uploaded_emoji.animated
                    else f"<:{uploaded_emoji.name}:{uploaded_emoji.id}>"
                )
                await self._silent_sync()
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay(f"{emoji.success} Uploaded emoji {emoji_md} `{file.filename[:-4]}`."),
                        color=config.color.green,
                    )
                )
                await ctx.respond(view=view)
            except Exception as e:
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay(f"{emoji.error} Failed to upload emoji `{file.filename[:-4]}`.\n{e}"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)
            png_buffer.close()
        else:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Please upload a valid zip file or a single `.png`/`.gif` file."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # Check emoji zip file
    @emoji.command(name="check-zip")
    @check.is_dev()
    @option("file", description="Upload emojis zip file.", type=discord.Attachment)
    async def check_emoji_zip(self, ctx: discord.ApplicationContext, file: discord.Attachment):
        """Checks the uploaded zip file for emojis."""
        await ctx.defer()
        if not file.filename.endswith(".zip"):
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Please upload a valid zip file."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return

        zip_buffer = BytesIO()
        await file.save(zip_buffer)
        zip_buffer.seek(0)

        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            namelist = zip_file.namelist()
            # Handle both flat structure and directory structure
            file_entries = [n for n in namelist if not n.endswith("/")]
            top_dirs = set()
            for n in namelist:
                parts = n.split("/")
                if len(parts) > 1 and parts[0]:
                    top_dirs.add(parts[0])

            if len(top_dirs) == 1:
                base_dir = list(top_dirs)[0]
                emoji_files = [f for f in file_entries if f.startswith(base_dir + "/") and f.endswith((".png", ".gif"))]
                emoji_names = [f.split("/")[-1][:-4] for f in emoji_files]
            else:
                emoji_files = [f for f in file_entries if "/" not in f and f.endswith((".png", ".gif"))]
                emoji_names = [f[:-4] for f in emoji_files]

            if not emoji_files:
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay(f"{emoji.error} No `.png` emoji files found in the zip."),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)
                return

            expected_emojis = set(Emoji.get_emoji_names())
            found_emojis = set(emoji_names)
            missing_emojis = expected_emojis - found_emojis
            extra_emojis = found_emojis - expected_emojis

            missing_list = "\n".join([f"{emoji.bullet} `{name}`" for name in sorted(missing_emojis)])
            extra_list = "\n".join([f"{emoji.bullet_red} `{name}`" for name in sorted(extra_emojis)])

            if missing_emojis:
                color = config.color.red
            elif extra_emojis:
                color = config.color.orange
            else:
                color = config.color.green
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay("## Emoji Zip Check"),
                    ui.TextDisplay(
                        f"Found `{len(emoji_files)}` emoji files in the zip. Expected `{len(expected_emojis)}` emojis."
                    ),
                    ui.Separator(),
                    ui.TextDisplay(
                        ("### Missing Emojis\n" + missing_list)
                        if missing_list
                        else f"{emoji.success} No missing emojis."
                    ),
                    ui.Separator(),
                    ui.TextDisplay(
                        ("### Extra Emojis\n" + extra_list) if extra_list else f"{emoji.success} No extra emojis."
                    ),
                    color=color,
                )
            )
            await ctx.respond(view=view)

        zip_buffer.close()

    # Sync app emojis
    @emoji.command(name="sync")
    @check.is_dev()
    async def sync_app_emojis(self, ctx: discord.ApplicationContext):
        """Syncs all emojis from the app."""
        await ctx.defer()
        emojis: list[discord.AppEmoji] = await self.client.fetch_emojis()
        if not emojis:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} No emojis found in the app."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        else:
            await ctx.respond(view=await self._sync_emoji_view(ctx))


def setup(client: Client):
    client.add_cog(Devs(client))
