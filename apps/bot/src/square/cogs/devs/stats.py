import asyncio
import datetime
import discord
import platform
import psutil
import sonolink
import time
from babel.dates import format_timedelta
from collections import defaultdict, deque
from discord import ui
from importlib.metadata import version
from square.cogs.devs.term import Term
from square.core import Client
from square.core.view import DesignerView, show_loading
from square.music.core import fetch_node_info
from square.utils.emoji import emoji
from square.utils.helpers import fmt_memory
from typing import Literal


def _has_stats(node: sonolink.Node) -> bool:
    return bool(node.is_connected and node.stats is not None)


class StatsView(DesignerView):
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
        self.history[key].append(value)
        return list(self.history[key])

    def _bar(self, percent: float) -> str:
        percent = min(max(percent, 0.0), 100.0)
        filled = int(round(self.BAR_WIDTH * percent / 100))
        return f"[{'#' * filled}{'-' * (self.BAR_WIDTH - filled)}] {percent:5.1f}%"

    def _axis(self, low: float, high: float) -> list[str]:
        values = [high - (high - low) * r / self.CHART_HEIGHT for r in range(self.CHART_HEIGHT + 1)]
        labels = [f"{v:.0f}" for v in values]
        for decimals in range(1, 4):
            if len(set(labels)) == len(labels):
                break
            labels = [f"{v:.{decimals}f}" for v in values]
        return labels

    def _chart(self, title: str, series: list[float]) -> list[str]:
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
        if not await show_loading(self, interaction, "Refreshing..."):
            return
        await self.build()
        await interaction.edit(view=self)

    async def _switch_page(self, interaction: discord.Interaction) -> None:
        if not await show_loading(self, interaction):
            return
        self.page = "lavalink" if self.page == "main" else "main"
        await self.build()
        await interaction.edit(view=self)

    async def _toggle_auto(self, interaction: discord.Interaction) -> None:
        self._cancel_auto()  # Before the edit, so a tick can't redraw over the loading state
        if not await show_loading(self, interaction):
            return
        self.auto = not self.auto
        if self.auto:
            self.history.clear()
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
        rss = self.process.memory_info().rss
        rows = [
            ("Square", f"v{version('square')}"),
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
