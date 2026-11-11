class MusicError(Exception):
    """A control the member can't use right now. The message is meant for them."""


class QueueChanged(MusicError):
    """The queue moved since the member last saw it, so the track they meant isn't where they pointed."""
