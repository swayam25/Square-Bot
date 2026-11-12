import discord
import enum


class Module(enum.StrEnum):
    LOGS = "logs"
    TICKETS = "tickets"
    INVITES = "invites"

    @property
    def label(self) -> str:
        return self.value.capitalize()


DEFAULT_MODULES = [Module.LOGS.value]


class ModuleOff(discord.CheckFailure):
    def __init__(self, module: Module):
        super().__init__(f"{module.label} is turned off in this server. A manager can turn it on from the dashboard.")
        self.module = module
