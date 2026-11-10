from discord.ext import commands
from square.core.settings import SettingsPage
from square.utils.emoji import Icon


class Cog(commands.Cog):
    """
    Base cog for Square.

    py-cord's own class keywords set the name & description (`name=`, `description=` or the docstring). This adds
    the help menu details: a cog with an `emoji` is a help category, the rest stay out of the menu.

    Example:
        ```py
        class Voice(Cog, name="Voice", description="Manage voice members.", emoji=emoji.voice, order=3): ...
        ```
    """

    # Dunder names like py-cord's `__cog_name__`: a plain `emoji` attribute would clash with commands such as `/emoji`
    __cog_emoji__: Icon | None = None
    __cog_order__: int = 0
    __cog_dev_only__: bool = False
    # Pages this cog adds to the `/settings` panel
    settings_pages: tuple[type[SettingsPage], ...] = ()

    def __init_subclass__(cls, *, emoji: Icon | None = None, order: int = 0, dev_only: bool = False, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.__cog_emoji__, cls.__cog_order__, cls.__cog_dev_only__ = emoji, order, dev_only

    @property
    def help_emoji(self) -> Icon | None:
        """The emoji shown for this cog's help category, or None to keep it out of help."""
        return self.__cog_emoji__

    @property
    def help_order(self) -> int:
        return self.__cog_order__

    @property
    def help_dev_only(self) -> bool:
        return self.__cog_dev_only__
