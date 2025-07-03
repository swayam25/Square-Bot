from tortoise import fields
from tortoise.models import Model
from typing import TypedDict


class DevTable(Model):
    id = fields.IntField(primary_key=True)
    user_id = fields.BigIntField(unique=True)
    joined_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dev"


class AutomemeField(TypedDict):
    channel_id: int | None
    subreddit: str | None


class GuildTable(Model):
    id = fields.IntField(primary_key=True)
    guild_id = fields.BigIntField(unique=True)
    mod_log_channel_id = fields.BigIntField(null=True)
    mod_cmd_log_channel_id = fields.BigIntField(null=True)
    msg_log_channel_id = fields.BigIntField(null=True)
    ticket_cmds = fields.BooleanField(default=True)
    ticket_log_channel_id = fields.BigIntField(null=True)
    media_only_channel_id = fields.BigIntField(null=True)
    autorole = fields.BigIntField(null=True)
    auto_meme: AutomemeField = fields.JSONField(default={"channel_id": None, "subreddit": None})

    class Meta:
        table = "guild"
