import discord
from discord.ext import commands
from square.db import cache
from square.modules import Module, ModuleOff


class Cog(commands.Cog):
    """
    Base class for every cog.

    py-cord's own class keywords set the name & description (`name=`, `description=` or the docstring). A cog with
    any command outside the owner's servers is a category on the website's commands page, sorted by `order`. A cog
    with a `module` refuses its commands in servers that turned that module off.

    Example:
        ```py
        class Voice(Cog, name="Voice", description="Manage voice members.", order=3): ...
        ```
    """

    # Dunder names like py-cord's `__cog_name__`: plain attributes would clash with commands of the same name
    __cog_order__: int = 0
    __cog_module__: Module | None = None

    def __init_subclass__(cls, *, order: int = 0, module: Module | None = None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.__cog_order__, cls.__cog_module__ = order, module

    def cog_check(self, ctx: discord.ApplicationContext) -> bool:
        module = self.__cog_module__
        if module and ctx.guild and not cache.enabled(ctx.guild.id, module):
            raise ModuleOff(module)
        return True

    @property
    def category_order(self) -> int:
        return self.__cog_order__
