import discord
from discord import ui
from discord.commands import option, slash_command
from square import logs
from square.core.view import DesignerView, button, dashboard_row, error_view, show_loading
from square.logs import memory
from square.utils import config
from square.utils.emoji import emoji
from square.utils.helpers import fmt_count

SNIPE_CHANNELS = [
    discord.ChannelType.text,
    discord.ChannelType.news,
    discord.ChannelType.voice,
    discord.ChannelType.stage_voice,
    discord.ChannelType.public_thread,
    discord.ChannelType.private_thread,
    discord.ChannelType.news_thread,
]


class SnipeView(DesignerView):
    def __init__(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.abc.GuildChannel | discord.Thread,
        kind: memory.SnipeKind,
        found: list[memory.Snipe],
    ):
        super().__init__(ctx=ctx, check_author_interaction=True, timeout=300)
        self.channel, self.kind, self.found, self.index = channel, kind, found, 0

    def build(self) -> DesignerView:
        if not self.found:
            return error_view(f"Nothing left to snipe in {self.channel.mention}.")
        self.index = min(self.index, len(self.found) - 1)
        snipe = self.found[self.index]
        saved = snipe.message
        edited = self.kind == "edited"
        rows = [
            f"{emoji.owner} **Author**: <@{saved.author_id}> (`{saved.author_name}`)",
            f"{emoji.channel} **Channel**: {self.channel.mention}",
            f"{emoji.date} **Sent**: {logs.when(saved.sent_at)}",
            f"{emoji.duration} **{'Edited' if edited else 'Deleted'}**: {logs.when(snipe.at)}",
        ]
        if snipe.deleted_by:
            rows.append(f"{emoji.user} **Deleted By**: {snipe.deleted_by}")
        if saved.files:
            rows.append(f"{emoji.img} **Files**: {', '.join(f'`{name}`' for name in saved.files)}")
        if saved.stickers:
            rows.append(f"{emoji.star} **Stickers**: {', '.join(f'`{name}`' for name in saved.stickers)}")
        if edited:
            rows.append(f"{emoji.note_red} **Before**:\n{logs.clip(saved.content) or 'Empty'}")
            rows.append(f"{emoji.note} **After**:\n{logs.clip(snipe.after or '') or 'Empty'}")
        elif saved.content:
            rows.append(f"{emoji.note} **Message**:\n{logs.clip(saved.content)}")

        self.clear_items()
        self.add_item(
            ui.Container(
                ui.Section(
                    ui.TextDisplay(f"## {'Edited' if edited else 'Deleted'} Message"),
                    ui.TextDisplay("\n".join(rows)),
                    accessory=ui.Thumbnail(saved.author_avatar),
                ),
                ui.Separator(),
                ui.TextDisplay(f"-# Viewing {fmt_count(self.index + 1)} of {fmt_count(len(self.found))}"),
                color=config.color.theme,
            )
        )
        last = len(self.found) - 1
        row = [
            button(lambda i: self._go(i, last if self.index == 0 else self.index - 1), emoji=emoji.previous_white),
            button(self._forget, label="Forget", emoji=emoji.bin_white, style=discord.ButtonStyle.red),
            button(lambda i: self._go(i, 0 if self.index == last else self.index + 1), emoji=emoji.next_white),
        ]
        if edited:
            url = f"https://discord.com/channels/{self.channel.guild.id}/{self.channel.id}/{saved.id}"
            row.append(
                ui.Button(label="Jump to message", emoji=emoji.messages_white, url=url, style=discord.ButtonStyle.link)
            )
        if len(self.found) == 1:
            row = row[1:2] + row[3:]
        self.add_item(ui.ActionRow(*row))
        return self

    async def _go(self, interaction: discord.Interaction, index: int) -> None:
        if await show_loading(self, interaction):
            self.index = index
            await interaction.edit_original_response(view=self.build())

    async def _forget(self, interaction: discord.Interaction) -> None:
        if not await show_loading(self, interaction):
            return
        snipe = self.found.pop(self.index)
        memory.forget_snipe(self.channel.guild.id, self.channel.id, self.kind, snipe)
        await interaction.edit_original_response(view=self.build())


class Snipe:
    @slash_command(name="snipe", contexts={discord.InteractionContextType.guild})
    @discord.default_permissions(manage_messages=True)
    @option(
        "type",
        description="Deleted or edited messages.",
        choices=[discord.OptionChoice("Deleted", "deleted"), discord.OptionChoice("Edited", "edited")],
        default="deleted",
        parameter_name="kind",
    )
    @option("user", description="Only messages from this person.", required=False)
    @option(
        "channel",
        description="Another channel. Leave empty for this one.",
        required=False,
        channel_types=SNIPE_CHANNELS,
    )
    async def snipe(
        self,
        ctx: discord.ApplicationContext,
        kind: str = "deleted",
        user: discord.User | None = None,
        channel: discord.abc.GuildChannel | discord.Thread | None = None,
    ):
        """Shows recently deleted or edited messages. Only you see the answer."""
        guild = ctx.guild
        channel = channel or ctx.channel
        if not memory.active(guild.id):
            view = error_view("Snipe needs the **Messages** log on. Turn it on from the dashboard.")
            view.add_item(dashboard_row(guild.id, "/logs"))
            await ctx.respond(view=view, ephemeral=True)
            return
        if isinstance(ctx.author, discord.Member) and not channel.permissions_for(ctx.author).read_message_history:
            await ctx.respond(view=error_view(f"You can't read {channel.mention}."), ephemeral=True)
            return
        wanted: memory.SnipeKind = "edited" if kind == "edited" else "deleted"
        found = [
            snipe
            for snipe in memory.snipes(guild.id, channel.id, wanted)
            if (user is None or snipe.message.author_id == user.id)
            and not logs.ignored(guild, channel.id, guild.get_member(snipe.message.author_id), snipe.message.bot)
        ]
        if not found:
            who = f" from {user.mention} (`{user.name}`)" if user else ""
            await ctx.respond(
                view=error_view(f"No {wanted} messages{who} to snipe in {channel.mention}."), ephemeral=True
            )
            return
        await ctx.respond(view=SnipeView(ctx, channel, wanted, found).build(), ephemeral=True)
