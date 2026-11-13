from square.modules import DEFAULT_MODULES
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
    modules: list[str] = fields.JSONField(default=lambda: list(DEFAULT_MODULES))
    media_only_channel_id = fields.BigIntField(null=True)
    autorole_ids: list[int] = fields.JSONField(default=list)
    autorole_bot_ids: list[int] = fields.JSONField(default=list)
    autorole_split = fields.BooleanField(default=False)
    dj_mode = fields.BooleanField(default=False)
    music_channel_id = fields.BigIntField(null=True)
    music_message_id = fields.BigIntField(null=True)
    music_stay_channel_id = fields.BigIntField(null=True)
    invite_fake_days = fields.IntField(default=7)
    ticket_category_id = fields.BigIntField(null=True)
    ticket_support_role_ids: list[int] = fields.JSONField(default=list)
    ticket_panel_channel_id = fields.BigIntField(null=True)
    ticket_panel_message_id = fields.BigIntField(null=True)
    ticket_max_open = fields.IntField(default=1)
    ticket_confirm_close = fields.BooleanField(default=True)
    ticket_next_number = fields.IntField(default=1)

    log_channels: fields.ReverseRelation[LogChannelTable]
    dj_roles: fields.ReverseRelation[DJRoleTable]
    autorole_users: fields.ReverseRelation[AutoroleUserTable]
    invite_joins: fields.ReverseRelation[InviteJoinTable]
    invite_bonuses: fields.ReverseRelation[InviteBonusTable]
    tickets: fields.ReverseRelation[TicketTable]

    class Meta:
        table = "guild"


class LogChannelTable(Model):
    id = fields.IntField(primary_key=True)
    guild: fields.ForeignKeyRelation[GuildTable] = fields.ForeignKeyField(
        "models.GuildTable", related_name="log_channels", on_delete=fields.CASCADE
    )
    log_type = fields.CharField(max_length=32)
    channel_id = fields.BigIntField()

    class Meta:
        table = "log_channel"
        unique_together = (("guild", "log_type"),)


class DJRoleTable(Model):
    id = fields.IntField(primary_key=True)
    guild: fields.ForeignKeyRelation[GuildTable] = fields.ForeignKeyField(
        "models.GuildTable", related_name="dj_roles", on_delete=fields.CASCADE
    )
    role_id = fields.BigIntField()

    class Meta:
        table = "dj_role"
        unique_together = (("guild", "role_id"),)


class AutoroleUserTable(Model):
    id = fields.IntField(primary_key=True)
    guild: fields.ForeignKeyRelation[GuildTable] = fields.ForeignKeyField(
        "models.GuildTable", related_name="autorole_users", on_delete=fields.CASCADE
    )
    user_id = fields.BigIntField()
    role_ids: list[int] = fields.JSONField(default=list)

    class Meta:
        table = "autorole_user"
        unique_together = (("guild", "user_id"),)


class InviteJoinTable(Model):
    id = fields.IntField(primary_key=True)
    guild: fields.ForeignKeyRelation[GuildTable] = fields.ForeignKeyField(
        "models.GuildTable", related_name="invite_joins", on_delete=fields.CASCADE
    )
    member_id = fields.BigIntField()
    inviter_id = fields.BigIntField(null=True)
    code = fields.CharField(max_length=32, null=True)
    joined_at = fields.DatetimeField()
    left_at = fields.DatetimeField(null=True)
    fake = fields.BooleanField(default=False)

    class Meta:
        table = "invite_join"
        unique_together = (("guild", "member_id"),)
        indexes = (("guild", "inviter_id"),)


class InviteBonusTable(Model):
    id = fields.IntField(primary_key=True)
    guild: fields.ForeignKeyRelation[GuildTable] = fields.ForeignKeyField(
        "models.GuildTable", related_name="invite_bonuses", on_delete=fields.CASCADE
    )
    user_id = fields.BigIntField()
    amount = fields.IntField(default=0)

    class Meta:
        table = "invite_bonus"
        unique_together = (("guild", "user_id"),)


class TicketTable(Model):
    id = fields.IntField(primary_key=True)
    guild: fields.ForeignKeyRelation[GuildTable] = fields.ForeignKeyField(
        "models.GuildTable", related_name="tickets", on_delete=fields.CASCADE
    )
    number = fields.IntField()
    channel_id = fields.BigIntField(unique=True)
    opener_id = fields.BigIntField()
    reason = fields.TextField()
    status = fields.CharField(max_length=8, default="open")  # open, closed or deleted
    claimed_by = fields.BigIntField(null=True)
    closed_by = fields.BigIntField(null=True)
    control_message_id = fields.BigIntField(null=True)
    log_message_id = fields.BigIntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    closed_at = fields.DatetimeField(null=True)
    message_count = fields.IntField(null=True)
    participant_ids: list[int] = fields.JSONField(default=list)

    members: fields.ReverseRelation[TicketMemberTable]

    class Meta:
        table = "ticket"
        unique_together = (("guild", "number"),)


class TicketMemberTable(Model):
    id = fields.IntField(primary_key=True)
    ticket: fields.ForeignKeyRelation[TicketTable] = fields.ForeignKeyField(
        "models.TicketTable", related_name="members", on_delete=fields.CASCADE
    )
    user_id = fields.BigIntField()
    added_by = fields.BigIntField()

    class Meta:
        table = "ticket_member"
        unique_together = (("ticket", "user_id"),)


class TicketTranscriptTable(Model):
    """Kept apart from the ticket row so listing tickets never loads their messages."""

    id = fields.IntField(primary_key=True)
    ticket: fields.OneToOneRelation[TicketTable] = fields.OneToOneField(
        "models.TicketTable", related_name="transcript", on_delete=fields.CASCADE
    )
    data = fields.JSONField()
    saved_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "ticket_transcript"


class TicketFileTable(Model):
    """A copy of a ticket's picture, since Discord's attachment links stop working after about a day."""

    id = fields.IntField(primary_key=True)
    ticket: fields.ForeignKeyRelation[TicketTable] = fields.ForeignKeyField(
        "models.TicketTable", related_name="files", on_delete=fields.CASCADE
    )
    attachment_id = fields.BigIntField()
    content_type = fields.CharField(max_length=32)
    size = fields.IntField()
    data = fields.BinaryField()

    class Meta:
        table = "ticket_file"
        unique_together = (("ticket", "attachment_id"),)
