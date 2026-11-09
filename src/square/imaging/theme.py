from dataclasses import dataclass, fields
from functools import cache
from materialyoucolor.blend import Blend
from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors
from materialyoucolor.hct import Hct
from materialyoucolor.palettes.tonal_palette import TonalPalette
from materialyoucolor.scheme.scheme_content import SchemeContent
from square.utils import config

type RGB = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class Scheme:
    """A dark color scheme. Field names are its color roles in snake_case."""

    primary: RGB
    on_primary: RGB
    primary_container: RGB
    on_primary_container: RGB
    secondary: RGB
    on_secondary: RGB
    secondary_container: RGB
    on_secondary_container: RGB
    tertiary: RGB
    on_tertiary: RGB
    tertiary_container: RGB
    on_tertiary_container: RGB
    surface: RGB
    surface_container_lowest: RGB
    surface_container_low: RGB
    surface_container: RGB
    surface_container_high: RGB
    surface_container_highest: RGB
    on_surface: RGB
    on_surface_variant: RGB
    outline: RGB
    outline_variant: RGB
    # Custom roles built from the config's green, orange and red, see `_custom`
    success: RGB
    success_container: RGB
    on_success_container: RGB
    warning: RGB
    warning_container: RGB
    on_warning_container: RGB
    error: RGB
    error_container: RGB
    on_error_container: RGB


def _rgb(argb: int) -> RGB:
    return (argb >> 16) & 0xFF, (argb >> 8) & 0xFF, argb & 0xFF


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part.title() for part in rest)


def _custom(name: str, color: int, seed: int) -> dict[str, RGB]:
    """A custom color: shifted toward the seed's hue so it sits with the palette, then toned for dark mode."""
    palette = TonalPalette.from_hct(Hct.from_int(Blend.harmonize(0xFF000000 | color, seed)))
    return {
        name: _rgb(palette.tone(80)),
        f"{name}_container": _rgb(palette.tone(30)),
        f"on_{name}_container": _rgb(palette.tone(90)),
    }


@cache
def scheme(seed: int | None = None) -> Scheme:
    """
    Builds the color scheme every image is drawn with.

    The Content variant is used because it keeps `primary_container` at the exact seed color, where the default
    TonalSpot variant would desaturate it.

    Args:
        seed (int | None): An RGB color like `0x1FCEEC`. Defaults to `colors.theme` in `config.toml`.
    """
    seed = 0xFF000000 | (config.color.theme if seed is None else seed)
    dynamic = SchemeContent(Hct.from_int(seed), is_dark=True, contrast_level=0.0)
    roles = MaterialDynamicColors()
    custom = (
        _custom("success", config.color.green, seed)
        | _custom("warning", config.color.orange, seed)
        | _custom("error", config.color.red, seed)
    )
    return Scheme(
        **{
            field.name: custom.get(field.name) or _rgb(getattr(roles, _camel(field.name)).get_argb(dynamic))
            for field in fields(Scheme)
        }
    )
