from tortoise import fields
from tortoise.models import Model


class DevTable(Model):
    id = fields.IntField(primary_key=True)
    user_id = fields.BigIntField(unique=True)
    joined_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dev"


class GuildTable(Model):
    id = fields.IntField(primary_key=True)
    guild_id = fields.BigIntField(unique=True)
    ticket_cmds = fields.BooleanField(default=False)
    media_only_channel_id = fields.BigIntField(null=True)
    autorole = fields.BigIntField(null=True)

    log_channels: fields.ReverseRelation[LogChannelTable]

    class Meta:
        table = "guild"


class LogChannelTable(Model):
    """One row per (guild, log type) pair, mapping a log category to its channel."""

    id = fields.IntField(primary_key=True)
    guild: fields.ForeignKeyRelation[GuildTable] = fields.ForeignKeyField(
        "models.GuildTable", related_name="log_channels", on_delete=fields.CASCADE
    )
    log_type = fields.CharField(max_length=32)
    channel_id = fields.BigIntField()

    class Meta:
        table = "log_channel"
        unique_together = (("guild", "log_type"),)
