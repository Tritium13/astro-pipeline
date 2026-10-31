"""Optional cleaning before reprojection: row/column destriping of i2d images.

NIRCam readout ("1/f") noise shows up as stripes along detector rows. In the
i2d frame they still run (roughly) along the image rows; after reprojection to
a north-up grid they are diagonal and much harder to remove. So this is done
on the i2d SCI image, *before* registration.

This is an approximation: a proper correction acts on the individual exposures
per detector/amplifier earlier in the calibration. Always inspect the
difference image (before - after): it must contain stripes only, no nebula.
"""
import warnings
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, median_filter, zoom
from astropy.io import fits


def background_mask(img, nsigma=3.0, grow_px=15):
    """True where the pixel can be used as background (finite, no source nearby).

    Sources = pixels brighter than median + nsigma * robust sigma (MAD),
    grown by `grow_px` pixels so that faint wings are excluded too.
    """
    finite = np.isfinite(img)
    v = img[finite]
    med = np.median(v)
    sigma = 1.4826 * np.median(np.abs(v - med))
    source = finite & (img > med + nsigma * sigma)
    near_source = distance_transform_edt(~source) <= grow_px
    return finite & ~near_source


def stripe_profile(img, bg, axis="rows", smooth=51, min_pixels=50):
    """High-pass profile of the background median along rows (or columns).

    1. median of the background pixels in every row
    2. rows with fewer than `min_pixels` background pixels are interpolated
    3. a running median over `smooth` rows is the slow part (real gradients)
    4. stripes = profile - slow part  (only row-to-row changes)
    """
    data = img if axis == "rows" else img.T
    m = bg if axis == "rows" else bg.T
    masked = np.where(m, data, np.nan)
    counts = m.sum(axis=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)   # rows without background -> NaN, handled below
        prof = np.nanmedian(masked, axis=1)
    good = (counts >= min_pixels) & np.isfinite(prof)
    if good.sum() < 2:
        return np.zeros(data.shape[0], np.float32), good
    idx = np.arange(prof.size)
    prof = np.interp(idx, idx[good], prof[good])
    slow = median_filter(prof, size=smooth, mode="nearest")
    return (prof - slow).astype(np.float32), good


def _segments(n, segment):
    if not segment or segment >= n:
        return [slice(0, n)]
    return [slice(s, min(s + segment, n)) for s in range(0, n, segment)]


def destripe(img, axis="rows", nsigma=3.0, grow_px=15, smooth=51, min_pixels=50, segment=None):
    """Subtract the stripe profile. Returns (cleaned, stripes, background mask).

    segment: if set (e.g. 512), the image is split into blocks of this many
    columns (axis="rows") and each block gets its own row profile. This
    catches stripes that do not run across the full width (separate readout
    amplifiers, several dithered exposures). `stripes` is then a 2-D array
    (n_rows x n_segments). Check the difference image for vertical seams.
    """
    bg = background_mask(img, nsigma, grow_px)
    data, m = (img, bg) if axis == "rows" else (img.T, bg.T)
    cleaned = data.astype(np.float32).copy()
    profiles = []
    for sl in _segments(data.shape[1], segment):
        prof, _ = stripe_profile(data[:, sl], m[:, sl], "rows", smooth, min_pixels)
        cleaned[:, sl] -= prof[:, None]
        profiles.append(prof)
    stripes = profiles[0] if len(profiles) == 1 else np.stack(profiles, axis=1)
    if axis != "rows":
        cleaned = cleaned.T
    return cleaned, stripes, bg


def stripe_strength(img, bg, axis="rows", smooth=51, min_pixels=50, segment=None):
    """Mean std of the stripe profiles (per column block if `segment` is set).

    Measure with a *smaller* segment than used for the correction to see
    residual stripes the correction could not catch.
    """
    data, m = (img, bg) if axis == "rows" else (img.T, bg.T)
    vals = []
    for sl in _segments(data.shape[1], segment):
        prof, good = stripe_profile(data[:, sl], m[:, sl], "rows", smooth, min_pixels)
        if good.any():
            vals.append(np.std(prof[good]))
    return float(np.mean(vals)) if vals else float("nan")


def write_cleaned_i2d(src, dest, sci, note):
    """Write PRIMARY + cleaned SCI (with original headers) to `dest`."""
    with fits.open(src, memmap=True) as hdul:
        prim = fits.PrimaryHDU(header=hdul[0].header)
        sci_hdu = fits.ImageHDU(data=sci.astype(np.float32), header=hdul["SCI"].header, name="SCI")
    sci_hdu.header["HISTORY"] = note
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    fits.HDUList([prim, sci_hdu]).writeto(dest, overwrite=True)
    return Path(dest)


# --- local-background variant -------------------------------------------------
# When the nebula fills the field there are no empty background pixels in many
# rows. Instead of empty sky we then use a *local* background: a heavily
# smoothed model of the image (like a rolling-ball background in Fiji). Stripes
# are a few pixels tall and vanish in the model, so they remain in the residual
# (image - model), even on top of the nebula.

def smooth_model(img, block=32):
    """Smooth large-scale model: NaN-median in block x block cells, bilinear upsampling."""
    ny, nx = img.shape
    py, px = -ny % block, -nx % block
    padded = np.pad(img, ((0, py), (0, px)), constant_values=np.nan)
    cells = padded.reshape(padded.shape[0] // block, block, padded.shape[1] // block, block)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        coarse = np.nanmedian(cells, axis=(1, 3))
    coarse = np.where(np.isfinite(coarse), coarse, np.nanmedian(coarse))
    model = zoom(coarse, block, order=1)[:ny, :nx]
    return model.astype(np.float32)


def residual_mask(resid, nsigma=5.0, grow_px=5):
    """True where the residual can be used: finite and no strong compact structure
    (stars, bright knots, sharp edges – positive *and* negative outliers)."""
    finite = np.isfinite(resid)
    v = resid[finite]
    med = np.median(v)
    sigma = 1.4826 * np.median(np.abs(v - med))
    outlier = finite & (np.abs(resid - med) > nsigma * sigma)
    return finite & ~(distance_transform_edt(~outlier) <= grow_px)


def destripe_local(img, axis="rows", block=16, nsigma=5.0, grow_px=5, smooth=51,
                   min_pixels=50, segment=512):
    """Destripe using a local background model instead of empty sky.

    Returns (cleaned, stripes, mask, residual). Check the difference image:
    sharp nebula edges running along rows are the main risk.
    """
    model = smooth_model(img, block)
    resid = img - model
    m = residual_mask(resid, nsigma, grow_px)
    data, mm = (resid, m) if axis == "rows" else (resid.T, m.T)
    out = (img if axis == "rows" else img.T).astype(np.float32).copy()
    profiles = []
    for sl in _segments(data.shape[1], segment):
        prof, _ = stripe_profile(data[:, sl], mm[:, sl], "rows", smooth, min_pixels)
        out[:, sl] -= prof[:, None]
        profiles.append(prof)
    stripes = profiles[0] if len(profiles) == 1 else np.stack(profiles, axis=1)
    if axis != "rows":
        out = out.T
    return out, stripes, m, resid


def stripe_strength_local(img, block=16, nsigma=5.0, grow_px=5, axis="rows", smooth=51,
                          min_pixels=50, segment=128):
    """Stripe strength measured on the local residual – works inside the nebula too."""
    resid = img - smooth_model(img, block)
    return stripe_strength(resid, residual_mask(resid, nsigma, grow_px), axis, smooth, min_pixels, segment)
