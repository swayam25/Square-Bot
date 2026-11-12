import discord
import enum


class Module(enum.StrEnum):
    """Features a server can switch off from the dashboard. Stored by value in `GuildTable.modules`."""

    LOGS = "logs"
    TICKETS = "tickets"
    INVITES = "invites"

    @property
    def label(self) -> str:
        return self.value.capitalize()


# Logs post nothing until a channel is picked, so they start on. Invite tracking costs Discord requests and tickets
# need setup, so those wait until a manager turns them on.
DEFAULT_MODULES = [Module.LOGS.value]


class ModuleOff(discord.CheckFailure):
    def __init__(self, module: Module):
        super().__init__(f"{module.label} is turned off in this server. A manager can turn it on from the dashboard.")
        self.module = module
