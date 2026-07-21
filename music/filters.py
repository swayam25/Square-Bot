from sonolink.models import ChannelMix, Distortion, Filters, Karaoke, LowPass, Rotation, Timescale, Tremolo, Vibrato


class EqPresets:
    """
    Declarative equalizer presets mapped onto sonolink filter models.

    Each table is keyed by the `/eq` choice label; :meth:`build` turns a (kind, variant)
    pair into a single-effect :class:`Filters` fragment ready to be combined with the
    player's other active presets.
    """

    karaoke = {
        "Light": {"level": 1.5, "mono_level": 0.8, "filter_band": 220.0, "filter_width": 100.0},
        "Medium": {"level": 2.0, "mono_level": 1.0, "filter_band": 220.0, "filter_width": 100.0},
        "Strong": {"level": 3.0, "mono_level": 1.2, "filter_band": 220.0, "filter_width": 100.0},
    }
    timescale = {
        "Nightcore": {"speed": 1.3, "pitch": 1.3, "rate": 1.0},
        "Daycore": {"speed": 0.7, "pitch": 0.7, "rate": 1.0},
    }
    tremolo = {
        "Subtle": {"frequency": 1.5, "depth": 0.3},
        "Medium": {"frequency": 2.0, "depth": 0.5},
        "Strong": {"frequency": 3.0, "depth": 0.7},
    }
    vibrato = {
        "Light": {"frequency": 1.5, "depth": 0.3},
        "Medium": {"frequency": 2.0, "depth": 0.5},
        "Heavy": {"frequency": 3.5, "depth": 0.8},
    }
    rotation = {
        "Slow": {"rotation_hz": 0.1},
        "Medium": {"rotation_hz": 0.2},
        "Fast": {"rotation_hz": 0.3},
    }
    lowpass = {
        "Light": {"smoothing": 5.0},
        "Medium": {"smoothing": 20.0},
        "Heavy": {"smoothing": 50.0},
    }
    channelmix = {
        "Mono": {"left_to_left": 0.5, "left_to_right": 0.5, "right_to_left": 0.5, "right_to_right": 0.5},
        "Left Only": {"left_to_left": 1.0, "left_to_right": 1.0, "right_to_left": 0.0, "right_to_right": 0.0},
        "Right Only": {"left_to_left": 0.0, "left_to_right": 0.0, "right_to_left": 1.0, "right_to_right": 1.0},
        "Swap": {"left_to_left": 0.0, "left_to_right": 1.0, "right_to_left": 1.0, "right_to_right": 0.0},
        "Wide Stereo": {"left_to_left": 1.0, "left_to_right": 0.3, "right_to_left": 0.3, "right_to_right": 1.0},
    }
    distortion = {
        "Light Crunch": {
            "sin_offset": 0.0,
            "sin_scale": 1.2,
            "cos_offset": 0.0,
            "cos_scale": 1.1,
            "tan_offset": 0.0,
            "tan_scale": 1.0,
            "offset": 0.05,
            "scale": 1.0,
        },
        "Heavy Metal": {
            "sin_offset": 0.1,
            "sin_scale": 1.5,
            "cos_offset": 0.1,
            "cos_scale": 1.4,
            "tan_offset": 0.05,
            "tan_scale": 1.2,
            "offset": 0.1,
            "scale": 1.1,
        },
        "Vintage": {
            "sin_offset": 0.0,
            "sin_scale": 1.1,
            "cos_offset": 0.0,
            "cos_scale": 1.05,
            "tan_offset": 0.0,
            "tan_scale": 1.0,
            "offset": 0.02,
            "scale": 0.95,
        },
        "Digital Clip": {
            "sin_offset": 0.2,
            "sin_scale": 2.0,
            "cos_offset": 0.2,
            "cos_scale": 1.8,
            "tan_offset": 0.1,
            "tan_scale": 1.5,
            "offset": 0.15,
            "scale": 1.2,
        },
    }

    @classmethod
    def build(cls, kind: str, variant: str) -> Filters:
        """Builds a single-effect :class:`Filters` fragment for the given preset kind and variant."""
        match kind:
            case "karaoke":
                return Filters(karaoke=Karaoke(**cls.karaoke[variant]))
            case "timescale":
                cfg = cls.timescale.get(variant)
                if cfg is None:  # Numeric speeds like "1.5x" scale speed and pitch together
                    value = float(variant.replace("x", ""))
                    cfg = {"speed": value, "pitch": value, "rate": 1.0}
                return Filters(timescale=Timescale(**cfg))
            case "tremolo":
                return Filters(tremolo=Tremolo(**cls.tremolo[variant]))
            case "vibrato":
                return Filters(vibrato=Vibrato(**cls.vibrato[variant]))
            case "rotation":
                return Filters(rotation=Rotation(**cls.rotation[variant]))
            case "lowpass":
                return Filters(low_pass=LowPass(**cls.lowpass[variant]))
            case "channelmix":
                return Filters(channel_mix=ChannelMix(**cls.channelmix[variant]))
            case "distortion":
                return Filters(distortion=Distortion(**cls.distortion[variant]))
            case _:
                raise KeyError(kind)
