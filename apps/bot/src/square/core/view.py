from collections.abc import Awaitable, Callable
from discord import AllowedMentions, ApplicationContext, ButtonStyle, Interaction
from discord.ui import Button, Container, DesignerModal, Item, Label, TextDisplay
from discord.ui import DesignerView as BaseDesignerView
from discord.ui.view import V
from square.utils import config
from square.utils.emoji import emoji

Callback = Callable[[Interaction], Awaitable[None]]


class DesignerView(BaseDesignerView):
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
    return DesignerView(Container(TextDisplay(f"{emoji.error} {text}"), color=config.color.red))


def success_view(text: str) -> DesignerView:
    return DesignerView(Container(TextDisplay(f"{emoji.success} {text}"), color=config.color.green))


def button(callback: Callback, **kwargs) -> Button:
    btn = Button(style=kwargs.pop("style", ButtonStyle.grey), **kwargs)
    btn.callback = callback
    return btn


def modal(title: str, *labels: Label, on_submit: Callback) -> DesignerModal:
    form = DesignerModal(*labels, title=title, timeout=600)
    form.callback = on_submit
    return form
