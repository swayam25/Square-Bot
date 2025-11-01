import aiohttp
import asyncio
import discord
import os
import sys
import textwrap
from core import Client
from core.view import DesignerView
from discord import ui
from discord.ext import commands
from io import BytesIO, StringIO
from utils import check, config
from utils.emoji import emoji

# This prevents clearing tasks during cog reloads
running_tasks = {}
manual_cancels = set()


class TaskManagerView(DesignerView):
    """View for managing running eval tasks."""

    def __init__(self, eval_cog, ctx: commands.Context, page: int = 1):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.eval_cog = eval_cog
        self.page = page
        self.items_per_page = 5
        self.build()

    def build(self):
        self.clear_items()
        tasks_list = list(running_tasks.items())
        total_tasks = len(tasks_list)

        if total_tasks == 0:
            container = ui.Container()
            container.add_item(ui.TextDisplay(f"{emoji.error} No running eval tasks."))
            container.color = config.color.red
            self.add_item(container)
            return

        # Main container with tasks
        container = ui.Container()
        container.add_item(ui.TextDisplay("## Running Eval Tasks"))

        # Calculate pagination
        total_pages = max(1, (total_tasks + self.items_per_page - 1) // self.items_per_page)
        start_idx = (self.page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_tasks = tasks_list[start_idx:end_idx]

        # Add task items
        for task_id, (task, task_ctx) in page_tasks:
            sec = ui.Section()
            status = "Starting" if task is None else ("Completed" if task.done() else "Running")
            sec.add_item(ui.TextDisplay(f"**Task `{task_id}`** [{status}]: {task_ctx.channel.mention}\n"))

            # Delete button
            delete_btn = ui.Button(emoji=emoji.bin_white, style=discord.ButtonStyle.grey, custom_id=f"delete_{task_id}")
            delete_btn.callback = lambda i, tid=task_id: self._delete_task(i, tid)
            sec.set_accessory(delete_btn)
            container.add_item(sec)

        if total_pages > 1:
            container.add_item(ui.Separator())
            container.add_item(ui.TextDisplay(f"-# Viewing Page {self.page}/{total_pages}"))

        self.add_item(container)

        # Control buttons
        self._add_control_buttons(total_pages)

    def _add_control_buttons(self, total_pages):
        """Add pagination and control buttons."""
        row2 = ui.ActionRow()

        if total_pages > 1:
            self.add_item(row1 := ui.ActionRow())
            # Pagination buttons (if needed)
            for emoji_icon, action in [(emoji.start_white, "start"), (emoji.previous_white, "previous")]:
                btn = ui.Button(emoji=emoji_icon, style=discord.ButtonStyle.grey)
                btn.callback = lambda i, a=action: self._paginate(i, a)
                row1.add_item(btn)
            # More pagination buttons
            for emoji_icon, action in [(emoji.next_white, "next"), (emoji.end_white, "end")]:
                btn = ui.Button(emoji=emoji_icon, style=discord.ButtonStyle.grey)
                btn.callback = lambda i, a=action: self._paginate(i, a)
                row1.add_item(btn)

        # Control buttons
        for emoji_icon, label, callback, disabled in [
            (emoji.bin_white, "Stop All", self._stop_all, False),
            (None, "‎ ", None, True),
            (emoji.restart_white, "Refresh", self._refresh, False),
        ]:
            btn = ui.Button(emoji=emoji_icon, label=label, style=discord.ButtonStyle.grey, disabled=disabled)
            btn.callback = callback
            row2.add_item(btn)
        self.add_item(row2)

    async def _delete_task(self, interaction: discord.Interaction, task_id: int):
        """Delete a specific task."""
        success = self.eval_cog.stop_task(task_id)
        embed_view = DesignerView(
            ui.Container(
                ui.TextDisplay(
                    f"{emoji.success} Task `{task_id}` stopped."
                    if success
                    else f"{emoji.error} Task `{task_id}` not found."
                ),
                color=config.color.green if success else config.color.red,
            )
        )
        self.build()
        await interaction.edit(view=self)
        await interaction.followup.send(view=embed_view, ephemeral=True)

    async def _stop_all(self, interaction: discord.Interaction):
        """Stop all running tasks."""
        stopped_count = self.eval_cog.stop_all_tasks()
        self.clear_items()
        container = ui.Container(
            ui.TextDisplay(f"{emoji.success} Stopped `{stopped_count}` running eval task(s)."),
            color=config.color.green,
        )
        self.add_item(container)
        await interaction.edit(view=self)
        await interaction.delete_original_response(delay=5)

    async def _refresh(self, interaction: discord.Interaction):
        """Refresh the task list."""
        self.eval_cog.cleanup_completed_tasks()
        self.build()
        await interaction.edit(view=self)

    async def _paginate(self, interaction: discord.Interaction, action: str):
        """Handle pagination."""
        total_tasks = len(running_tasks)
        total_pages = max(1, (total_tasks + self.items_per_page - 1) // self.items_per_page)

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


class Eval(commands.Cog):
    """Simplified eval cog with integrated task management and code execution."""

    def __init__(self, client: Client):
        self.client = client

    # Task Management Methods (previously in TaskManager class)
    def add_task(self, task, ctx):
        """Add a task to the running tasks."""
        task_id = max(running_tasks.keys(), default=0) + 1
        running_tasks[task_id] = (task, ctx)
        return task_id

    def cleanup_completed_tasks(self):
        """Clean up completed tasks."""
        completed_ids = [task_id for task_id, (task, _) in running_tasks.items() if task is not None and task.done()]
        for task_id in completed_ids:
            manual_cancels.discard(task_id)
            del running_tasks[task_id]

    def stop_all_tasks(self):
        """Stop all running tasks."""
        stopped_count = 0
        for task_id, (task, _) in list(running_tasks.items()):
            if task is not None and not task.done():
                manual_cancels.add(task_id)
                task.cancel()
                stopped_count += 1
        running_tasks.clear()
        return stopped_count

    def stop_task(self, task_id):
        """Stop a specific task."""
        if task_id in running_tasks:
            task, _ = running_tasks[task_id]
            if task is not None and not task.done():
                manual_cancels.add(task_id)
                task.cancel()
            del running_tasks[task_id]
            return True
        return False

    # Code Processing Methods (previously in CodeProcessor class)
    @staticmethod
    def clean_code_block(code: str) -> str:
        """Extract code from Discord code blocks."""
        code = code.strip()
        if code.startswith("```") and code.endswith("```"):
            code = code[3:-3].strip()
            if "\n" in code:
                first_line, rest = code.split("\n", 1)
                if first_line.strip().isalpha() and len(first_line.strip()) <= 10:
                    return rest
        return code.strip("` ")

    @staticmethod
    def is_simple_message(code: str) -> bool:
        """Check if code is a simple message."""
        return not any(char in code for char in "()=+-*/[]{}")

    # Code Execution Methods (previously in CodeExecutor class)
    def create_execution_env(self, ctx):
        """Create execution environment."""

        async def fetch(url, method="GET", **kwargs):
            """Simple HTTP utility function for eval environment."""
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **kwargs) as response:
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        return await response.json()
                    else:
                        return await response.text()

        return {
            "client": self.client,
            "discord": discord,
            "commands": commands,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "asyncio": asyncio,
            "os": os,
            "fetch": fetch,
        }

    async def execute_code(self, code: str, env: dict, timeout: float = 30.0):
        """Execute code with timeout."""
        stdout = sys.stdout
        sys.stdout = output_buffer = StringIO()
        try:
            exec(f"async def __eval_function():\n{textwrap.indent(code, '    ')}", env)
            result = await asyncio.wait_for(env["__eval_function"](), timeout=timeout)
            return output_buffer.getvalue(), result
        except TimeoutError as e:
            raise Exception("Execution timed out after 30 seconds") from e
        except Exception as e:
            raise e
        finally:
            sys.stdout = stdout

    async def execute_background_task(self, code: str, env: dict, ctx: commands.Context, task_id: int):
        """Execute code as background task."""
        try:
            output, result = await self.execute_code(code, env, timeout=None)
            await self.send_task_result(ctx, task_id, output, result)
        except asyncio.CancelledError:
            if task_id not in manual_cancels:
                embed_view = DesignerView(
                    ui.Container(
                        ui.TextDisplay(f"{emoji.error} Task `{task_id}` was cancelled."),
                        color=config.color.red,
                    )
                )
                await ctx.send(view=embed_view)
        except Exception as e:
            embed_view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Task `{task_id}` failed."),
                    ui.TextDisplay(f"```\n{str(e)}\n```"),
                    color=config.color.red,
                )
            )
            await ctx.send(view=embed_view)
        finally:
            running_tasks.pop(task_id, None)

    async def send_task_result(self, ctx, task_id, output, result):
        """Send task completion result."""
        response = f"{emoji.success} Task `{task_id}` completed.\n"
        if output:
            response += f"{emoji.console_green} **Output**:\n```sh\n{output}\n```\n"
        if result is not None:
            response += f"{emoji.enter_green} **Return Value**:\n```sh\n{result}\n```"

        return await self.send_result(ctx, response, output, result, task_id)

    async def send_result(self, ctx, response: str, output: str = "", result=None, task_id: int = None):
        """Send result with file attachment if too large."""
        if len(response) > 2000:
            full_content = str(output or result) if output or result else ""
            filename = f"task_{task_id}_output.txt" if task_id else "eval_output.txt"
            file = discord.File(BytesIO(full_content.encode()), filename=filename)
            return await ctx.send(file=file)
        else:
            view = DesignerView(ui.Container(ui.TextDisplay(response), color=config.color.green))
            return await ctx.send(view=view)

    # Command Handlers
    async def handle_control_commands(self, ctx: commands.Context, code: str):
        """Handle stop and list commands."""
        code_lower = code.lower()

        if code_lower in ["stop", "cancel", "kill"]:
            if not running_tasks:
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay(f"{emoji.error} No running eval tasks to stop."),
                        color=config.color.red,
                    )
                )
                return await ctx.reply(view=view, mention_author=False)

            stopped_count = self.stop_all_tasks()
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Stopped `{stopped_count}` running eval task(s)."),
                    color=config.color.green,
                )
            )
            return await ctx.reply(view=view, mention_author=False)

        if code_lower in ["list", "tasks", "running"]:
            view = TaskManagerView(self, ctx)
            return await ctx.reply(view=view, mention_author=False)

        return None

    @commands.command(name="eval", hidden=True)
    @check.is_owner()
    async def _eval(self, ctx: commands.Context, *, code: str = ""):
        """Evaluates arbitrary Python code."""
        if not code:
            return
        control_result = await self.handle_control_commands(ctx, code)
        if control_result:
            return
        code = self.clean_code_block(code)
        if self.is_simple_message(code):
            return await ctx.send(code)
        env = self.create_execution_env(ctx)
        task_id = self.add_task(None, ctx)  # Reserve ID first
        task = asyncio.create_task(self.execute_background_task(code, env, ctx, task_id))
        running_tasks[task_id] = (task, ctx)  # Update with actual task
        self.cleanup_completed_tasks()

        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.success} Started eval task `{task_id}`."),
                ui.TextDisplay("-# Use `eval list` to manage running tasks."),
                color=config.color.green,
            )
        )
        await ctx.reply(view=view, mention_author=False, delete_after=2)


def setup(client: Client):
    client.add_cog(Eval(client))
