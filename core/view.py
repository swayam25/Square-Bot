from discord import AllowedMentions, ApplicationContext, Interaction
from discord.ui import Container, Item, TextDisplay
from discord.ui import DesignerView as BaseDesignerView
from discord.ui.view import V
from utils import config
from utils.emoji import emoji


class DesignerView(BaseDesignerView):
    """
    A custom DesignerView class for Discord UI components derived from `discord.ui.DesignerView`.

    Parameters:
        *items (Item[V]): The items to be added to the view.
        timeout (float | None): The timeout for the view, defaults to 180.0 seconds.
        disable_on_timeout (bool): Whether to disable all items on timeout, defaults to True.
        allowed_mentions (AllowedMentions | None): Allowed mentions for the view's messages. Defaults to no mentions.
        ctx (ApplicationContext | None): The application context for the view.
        check_author_interaction (bool): Whether to check if the interaction author is the command author.
    """

    def __init__(
        self,
        *items: Item[V],
        timeout: float | None = 180.0,
        disable_on_timeout: bool = True,
        allowed_mentions: AllowedMentions | None = None,
        ctx: ApplicationContext | None = None,
        check_author_interaction: bool = False,
    ):
        super().__init__(*items, timeout=timeout)
        self.timeout = timeout
        self.disable_on_timeout = disable_on_timeout
        self.allowed_mentions = allowed_mentions
        self.ctx = ctx
        self.check_author_interaction = check_author_interaction
        if self.check_author_interaction and not self.ctx:
            raise ValueError("Context is required for author interaction check.")

    async def interaction_check(self, interaction: Interaction) -> bool:
        """
        A callback that is called when an interaction happens within the view
        that checks whether the view should process item callbacks for the interaction.

        Parameters:
            interaction (Interaction): The interaction that occurred.
        """
        if self.check_author_interaction:
            if interaction.user != self.ctx.author:
                view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} You are not the author of this command."),
                        color=config.color.red,
                    )
                )
                await interaction.response.send_message(embed=view, ephemeral=True)
                return False
            else:
                return True
        return True

    async def on_timeout(self) -> None:
        """A callback that is called when a view's timeout elapses without being explicitly stopped."""
        if self.disable_on_timeout:
            self.disable_all_items()
            if not self._message or self._message.flags.ephemeral:
                message = self.parent
            else:
                message = self.message
            if message:
                m = await message.edit(view=self)
                if m:
                    self._message = m
