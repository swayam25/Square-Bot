from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextStyle:
    size: float
    line_height: float
    weight: int = 400


class Type:
    """The type scale, in dp."""

    DISPLAY_LARGE = TextStyle(57, 64)
    DISPLAY_MEDIUM = TextStyle(45, 52)
    DISPLAY_SMALL = TextStyle(36, 44)
    HEADLINE_LARGE = TextStyle(32, 40)
    HEADLINE_MEDIUM = TextStyle(28, 36)
    HEADLINE_SMALL = TextStyle(24, 32)
    TITLE_LARGE = TextStyle(22, 28)
    TITLE_MEDIUM = TextStyle(16, 24, 500)
    TITLE_SMALL = TextStyle(14, 20, 500)
    BODY_LARGE = TextStyle(16, 24)
    BODY_MEDIUM = TextStyle(14, 20)
    BODY_SMALL = TextStyle(12, 16)
    LABEL_LARGE = TextStyle(14, 20, 500)
    LABEL_MEDIUM = TextStyle(12, 16, 500)
    LABEL_SMALL = TextStyle(11, 16, 500)


class Shape:
    """Corner radii, in dp. `FULL` rounds the shorter side into a pill or circle."""

    NONE = 0
    EXTRA_SMALL = 4
    SMALL = 8
    MEDIUM = 12
    LARGE = 16
    EXTRA_LARGE = 28
    FULL = -1
