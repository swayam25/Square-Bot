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
    giveaways: fields.ReverseRelation[GiveawayTable]
    starboards: fields.ReverseRelation[StarboardTable]
    starboard_votes: fields.ReverseRelation[StarboardVoteTable]
    automod_rules: fields.ReverseRelation[AutomodRuleTable]
    warnings: fields.ReverseRelation[WarningTable]
    warn_punishments: fields.ReverseRelation[WarnPunishmentTable]

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


class GiveawayTable(Model):
    id = fields.IntField(primary_key=True)
    guild: fields.ForeignKeyRelation[GuildTable] = fields.ForeignKeyField(
        "models.GuildTable", related_name="giveaways", on_delete=fields.CASCADE
    )
    status = fields.CharField(max_length=10, default="scheduled")  # scheduled, running or ended
    channel_id = fields.BigIntField()
    message_id = fields.BigIntField(null=True, unique=True)
    host_id = fields.BigIntField()
    prize = fields.CharField(max_length=256)
    description = fields.TextField(default="")
    winner_count = fields.IntField(default=1)
    starts_at = fields.DatetimeField()
    ends_at = fields.DatetimeField()
    ended_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    required_role_ids: list[int] = fields.JSONField(default=list)
    require_all_roles = fields.BooleanField(default=False)
    blocked_role_ids: list[int] = fields.JSONField(default=list)
    min_account_days = fields.IntField(default=0)
    min_member_days = fields.IntField(default=0)
    min_invites = fields.IntField(default=0)
    bonus_roles: list[list[int]] = fields.JSONField(default=list)  # [role_id, extra entries] pairs
    ping_role_id = fields.BigIntField(null=True)
    winner_role_id = fields.BigIntField(null=True)
    color = fields.CharField(max_length=7, null=True)
    image_url = fields.TextField(null=True)
    image_file = fields.CharField(max_length=64, null=True)  # Uploaded image's file name
    button_label = fields.CharField(max_length=40, default="Enter")
    button_emoji = fields.CharField(max_length=100, null=True)
    button_style = fields.CharField(max_length=8, default="blurple")
    entry_count = fields.IntField(default=0)
    winner_ids: list[int] = fields.JSONField(default=list)
    drawn_ids: list[int] = fields.JSONField(default=list)  # Everyone ever drawn, so rerolls never pick them again

    entries: fields.ReverseRelation[GiveawayEntryTable]

    class Meta:
        table = "giveaway"
        indexes = (("guild", "status"), ("status", "starts_at"), ("status", "ends_at"))


class GiveawayEntryTable(Model):
    id = fields.IntField(primary_key=True)
    giveaway: fields.ForeignKeyRelation[GiveawayTable] = fields.ForeignKeyField(
        "models.GiveawayTable", related_name="entries", on_delete=fields.CASCADE
    )
    user_id = fields.BigIntField()
    bonus = fields.IntField(default=0)
    entered_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "giveaway_entry"
        unique_together = (("giveaway", "user_id"),)


class StarboardTable(Model):
    id = fields.IntField(primary_key=True)
    guild: fields.ForeignKeyRelation[GuildTable] = fields.ForeignKeyField(
        "models.GuildTable", related_name="starboards", on_delete=fields.CASCADE
    )
    channel_id = fields.BigIntField()
    enabled = fields.BooleanField(default=True)
    emojis: list[str] = fields.JSONField(default=lambda: ["⭐"])
    downvote_emojis: list[str] = fields.JSONField(default=list)
    threshold = fields.IntField(default=3)
    drop_below = fields.IntField(null=True)  # Posts whose score falls under this leave the board, None keeps them
    self_vote = fields.BooleanField(default=False)
    allow_bots = fields.BooleanField(default=True)
    channel_mode = fields.CharField(max_length=8, default="all")  # all, only or except
    channel_ids: list[int] = fields.JSONField(default=list)
    blocked_role_ids: list[int] = fields.JSONField(default=list)
    max_age_days = fields.IntField(null=True)
    follow_deletes = fields.BooleanField(default=False)  # Deleting the original deletes its post too
    color = fields.CharField(max_length=7, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    posts: fields.ReverseRelation[StarboardPostTable]

    class Meta:
        table = "starboard"
        unique_together = (("guild", "channel_id"),)


class StarboardPostTable(Model):
    id = fields.IntField(primary_key=True)
    board: fields.ForeignKeyRelation[StarboardTable] = fields.ForeignKeyField(
        "models.StarboardTable", related_name="posts", on_delete=fields.CASCADE
    )
    message_id = fields.BigIntField()
    channel_id = fields.BigIntField()
    author_id = fields.BigIntField()
    post_id = fields.BigIntField(null=True, unique=True)
    webhook_id = fields.BigIntField(null=True)  # The webhook that sent the post, None when the bot did
    score = fields.IntField(default=0)
    emoji = fields.CharField(max_length=64, null=True)  # The vote emoji the score came from
    forced = fields.BooleanField(default=False)
    uploaded: dict[str, str] = fields.JSONField(
        default=dict
    )  # Source attachment ID -> file name re-uploaded on the post
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "starboard_post"
        unique_together = (("board", "message_id"),)
        indexes = (("board", "score"), ("board", "author_id"), ("message_id",))


class StarboardVoteTable(Model):
    """
    Reactions with a board emoji, bots included, so the stored count matches Discord's and drift shows.

    Only kept while a message is being voted on: the sweep drops old ones, and a later vote reads them back from
    Discord when its count no longer matches.
    """

    id = fields.IntField(primary_key=True)
    guild: fields.ForeignKeyRelation[GuildTable] = fields.ForeignKeyField(
        "models.GuildTable", related_name="starboard_votes", on_delete=fields.CASCADE
    )
    message_id = fields.BigIntField()
    channel_id = fields.BigIntField()
    user_id = fields.BigIntField()
    emoji = fields.CharField(max_length=32)  # Custom emoji ID or the Unicode emoji without variation selectors
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "starboard_vote"
        unique_together = (("message_id", "user_id", "emoji"),)
        indexes = (("channel_id",), ("created_at",))


class AutomodRuleTable(Model):
    id = fields.IntField(primary_key=True)
    guild: fields.ForeignKeyRelation[GuildTable] = fields.ForeignKeyField(
        "models.GuildTable", related_name="automod_rules", on_delete=fields.CASCADE
    )
    kind = fields.CharField(max_length=16)  # media, invites, flood, duplicates, caps or emojis
    enabled = fields.BooleanField(default=True)
    amount = fields.IntField(null=True)  # The rule's limit: messages, repeats, percent of capitals or emojis
    seconds = fields.IntField(null=True)
    channel_ids: list[int] = fields.JSONField(default=list)  # Media-only channels
    delete_message = fields.BooleanField(default=True)
    warn = fields.BooleanField(default=False)
    notify = fields.BooleanField(default=True)
    exempt_role_ids: list[int] = fields.JSONField(default=list)
    exempt_channel_ids: list[int] = fields.JSONField(default=list)

    class Meta:
        table = "automod_rule"
        unique_together = (("guild", "kind"),)


class WarningTable(Model):
    id = fields.IntField(primary_key=True)
    guild: fields.ForeignKeyRelation[GuildTable] = fields.ForeignKeyField(
        "models.GuildTable", related_name="warnings", on_delete=fields.CASCADE
    )
    user_id = fields.BigIntField()
    moderator_id = fields.BigIntField(null=True)  # None when AutoMod gave it
    reason = fields.TextField(default="")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "warning"
        indexes = (("guild", "user_id"),)


class WarnPunishmentTable(Model):
    id = fields.IntField(primary_key=True)
    guild: fields.ForeignKeyRelation[GuildTable] = fields.ForeignKeyField(
        "models.GuildTable", related_name="warn_punishments", on_delete=fields.CASCADE
    )
    warnings = fields.IntField()
    action = fields.CharField(max_length=8)  # timeout, kick or ban
    seconds = fields.IntField(null=True)

    class Meta:
        table = "warn_punishment"
        unique_together = (("guild", "warnings"),)
