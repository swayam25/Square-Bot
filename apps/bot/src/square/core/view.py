from discord import AllowedMentions, ApplicationContext, Interaction
from discord.ui import Container, Item, TextDisplay
from discord.ui import DesignerView as BaseDesignerView
from discord.ui.view import V
from square.utils import config
from square.utils.emoji import emoji


class DesignerView(BaseDesignerView):
    """
    A custom DesignerView class for Discord UI components derived from :class:`discord.ui.DesignerView`.

    Args:
        *items (:class:`Item`[V]): The items to be added to the view.
        timeout (float | None): The timeout for the view, defaults to 180.0 seconds.
        disable_on_timeout (bool): Whether to disable all items on timeout, defaults to True.
        allowed_mentions (:class:`AllowedMentions` | None): Allowed mentions for the view's messages. Defaults to no mentions.
        ctx (:class:`ApplicationContext` | None): The application context for the view.
        check_author_interaction (bool): Whether to check if the interaction author is the command author.
        store (bool): Whether py-cord keeps the view to run its callbacks. Off for views handled by a listener.
    """

    def __init__(
        self,
        *items: Item[V],
        timeout: float | None = 180.0,
        disable_on_timeout: bool = True,
        allowed_mentions: AllowedMentions | None = None,
        ctx: ApplicationContext | None = None,
        check_author_interaction: bool = False,
        store: bool = True,
    ):
        super().__init__(*items, timeout=timeout, store=store)
        self.timeout = timeout
        self.disable_on_timeout = disable_on_timeout
        self.allowed_mentions = allowed_mentions
        self.ctx = ctx
        self.check_author_interaction = check_author_interaction
        if self.check_author_interaction and not self.ctx:
            raise ValueError("Context is required for author interaction check.")

    async def interaction_check(self, interaction: Interaction) -> bool:
        """
        A callback that is called when an interaction happens within the view that checks whether the view should process item callbacks for the interaction.

        Args:
            interaction (:class:`Interaction`): The interaction that occurred.
        """
        if self.check_author_interaction:
            if interaction.user != self.ctx.author:
                view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} You are not the author of this command."),
                        color=config.color.red,
                    ),
                    disable_on_timeout=False,
                )
                await interaction.response.send_message(view=view, ephemeral=True)
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


async def show_loading(
    view: BaseDesignerView, interaction: Interaction, label: str | None = None, *, custom_id: str | None = None
) -> bool:
    """
    Disables the view and turns the pressed button into a loading one, until the view is next redrawn.

    Args:
        view (:class:`discord.ui.DesignerView`): The view on the pressed message.
        interaction (:class:`Interaction`): The press, answered by this edit.
        label (str | None): The button's status text. Icon-only buttons leave it out.
        custom_id (str | None): The pressed button, when `interaction` can't say, e.g. a modal submit.

    Returns:
        bool: False when the press landed while the view was already loading. It's answered, so just stop.
    """
    pressed = view.get_item(custom_id or (interaction.data or {}).get("custom_id"))
    if pressed and pressed.disabled:
        await interaction.response.defer()
        return False
    view.disable_all_items()
    if pressed:
        pressed.emoji = emoji.loading_white
        if label:
            pressed.label = label
    await interaction.edit(view=view)
    return True


def error_view(text: str) -> DesignerView:
    """Square's standard error reply: the error emoji and the text in a red container."""
    return DesignerView(Container(TextDisplay(f"{emoji.error} {text}"), color=config.color.red))


def success_view(text: str) -> DesignerView:
    """Square's standard success reply: the success emoji and the text in a green container."""
    return DesignerView(Container(TextDisplay(f"{emoji.success} {text}"), color=config.color.green))
