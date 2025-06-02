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
    mod_log_channel_id = fields.BigIntField(null=True)
    mod_cmd_log_channel_id = fields.BigIntField(null=True)
    msg_log_channel_id = fields.BigIntField(null=True)
    ticket_cmds = fields.BooleanField(default=True)
    ticket_log_channel_id = fields.BigIntField(null=True)
    autorole = fields.BigIntField(null=True)

    class Meta:
        table = "guild"
