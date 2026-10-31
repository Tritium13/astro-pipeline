"""Stage 5: hues and additive colour mixing of any number of filters."""
import colorsys

import numpy as np

from .bands import sort_bands


def hue(deg, s=1.0):
    """RGB (0–1) for a hue angle in degrees (0 red, 120 green, 240 blue) and saturation s."""
    return np.array(colorsys.hsv_to_rgb((deg % 360) / 360, s, 1.0), dtype=np.float32)


def chromatic_mapping(bands, start=240.0, end=0.0):
    """Variant A: hues evenly spaced by wavelength order, shortest = blue, longest = red."""
    bands = sort_bands(bands)
    n = len(bands)
    if n == 1:
        return {bands[0]: hue(0, 0.0)}
    return {b: hue(start + i * (end - start) / (n - 1)) for i, b in enumerate(bands)}


def mapping_from_degrees(deg_by_band, sat_by_band=None):
    """Build a mapping from hue angles (and optional saturations) per band."""
    sat_by_band = sat_by_band or {}
    return {b: hue(d, sat_by_band.get(b, 1.0)) for b, d in deg_by_band.items()}


def compose(images, mapping, weights=None):
    """RGB = sum(w * img * colour) / sum(w * colour) per channel, clipped to 0–1.

    The denominator makes a pixel that is 1 in all bands exactly white.
    """
    weights = weights or {}
    first = next(iter(images.values()))
    num = np.zeros(first.shape + (3,), np.float32)
    den = np.zeros(3, np.float32)
    for b, col in mapping.items():
        w = weights.get(b, 1.0)
        num += w * images[b][..., None] * np.asarray(col, np.float32)
        den += w * np.asarray(col, np.float32)
    return np.clip(num / np.maximum(den, 1e-6), 0, 1)
