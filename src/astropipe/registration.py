"""Stage 3: bring all filters onto one common sky grid and check alignment."""
import time
import warnings
from pathlib import Path

import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
from astropy.wcs.utils import proj_plane_pixel_scales
from reproject import reproject_adaptive
from reproject.mosaicking import find_optimal_celestial_wcs

warnings.simplefilter("ignore", FITSFixedWarning)


def target_grid(files, resolution_arcsec=0.063):
    """North-up TAN grid covering all input images at the given pixel scale.

    files: iterable of i2d paths. Only headers are read.
    Returns (wcs_out, shape_out).
    """
    inputs = []
    for f in files:
        hdr = fits.getheader(f, extname="SCI")
        inputs.append(((hdr["NAXIS2"], hdr["NAXIS1"]), WCS(hdr)))
    return find_optimal_celestial_wcs(inputs, resolution=resolution_arcsec * u.arcsec)


def pixel_scale_arcsec(wcs):
    return (proj_plane_pixel_scales(wcs) * u.deg).to(u.arcsec).value


def reproject_file(path, wcs_out, shape_out):
    """Reproject the SCI extension of one i2d file (surface brightness preserved)."""
    with fits.open(path, memmap=True) as hdul:
        sci = hdul["SCI"].data.astype(np.float32)
        wcs_in = WCS(hdul["SCI"].header)
        bunit = hdul["SCI"].header.get("BUNIT", "")
    array, footprint = reproject_adaptive((sci, wcs_in), wcs_out, shape_out=shape_out,
                                          conserve_flux=False)
    return array.astype(np.float32), footprint.astype(np.float32), bunit


def reproject_all(files_by_band, wcs_out, shape_out, out_dir, prefix, overwrite=False):
    """Reproject every band and save as FITS (primary = SCI, extension FOOTPRINT).

    files_by_band: dict band -> i2d path. Returns dict band -> output path.
    Existing outputs are reused unless overwrite=True.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    for band, path in files_by_band.items():
        out_path = out_dir / f"{prefix}_{band.lower()}_reproj.fits"
        out[band] = out_path
        if out_path.exists() and not overwrite:
            print(f"{band:<7} exists -> {out_path.name}")
            continue
        t0 = time.perf_counter()
        array, footprint, bunit = reproject_file(path, wcs_out, shape_out)
        hdr = wcs_out.to_header()
        hdr["BAND"] = (band, "filter defining the passband")
        hdr["BUNIT"] = bunit
        hdr["SRCFILE"] = Path(path).name
        hdr["REPROJ"] = ("reproject_adaptive", "conserve_flux=False")
        fits.HDUList([
            fits.PrimaryHDU(data=array, header=hdr),
            fits.ImageHDU(data=footprint, header=wcs_out.to_header(), name="FOOTPRINT"),
        ]).writeto(out_path, overwrite=True)
        print(f"{band:<7} {time.perf_counter() - t0:6.1f} s -> {out_path.name}")
    return out


def _centroid(img, y, x, half=5):
    box = img[y - half:y + half + 1, x - half:x + half + 1]
    if box.shape != (2 * half + 1,) * 2 or not np.all(np.isfinite(box)):
        return None
    edge = np.concatenate([box[0], box[-1], box[1:-1, 0], box[1:-1, -1]])
    w = np.clip(box - np.median(edge), 0, None)
    if w.sum() <= 0:
        return None
    yy, xx = np.mgrid[-half:half + 1, -half:half + 1]
    return y + (w * yy).sum() / w.sum(), x + (w * xx).sum() / w.sum()


def star_offsets(images, ref_band, num_peaks=12, min_distance=40, exclude_border=60, half=5):
    """Centroid offsets (px) of bright stars in every band relative to `ref_band`.

    Returns dict band -> list of offsets (stars with NaN in the box are skipped).
    """
    from skimage.feature import peak_local_max
    ref = np.nan_to_num(images[ref_band], nan=0.0)
    peaks = peak_local_max(ref, min_distance=min_distance, num_peaks=num_peaks,
                           exclude_border=exclude_border)
    offsets = {b: [] for b in images}
    for y, x in peaks:
        c_ref = _centroid(images[ref_band], y, x, half)
        if c_ref is None:
            continue
        for b, img in images.items():
            c = _centroid(img, y, x, half)
            if c is not None:
                offsets[b].append(float(np.hypot(c[0] - c_ref[0], c[1] - c_ref[1])))
    return offsets


def star_shifts(images, ref_band, num_peaks=12, min_distance=40, exclude_border=60, half=5):
    """Signed centroid offsets (dy, dx) in px of bright stars, band minus `ref_band`.

    Returns dict band -> array of shape (n_stars, 2). A consistent median with
    small scatter indicates a real registration shift (e.g. between instruments).
    """
    from skimage.feature import peak_local_max
    ref = np.nan_to_num(images[ref_band], nan=0.0)
    peaks = peak_local_max(ref, min_distance=min_distance, num_peaks=num_peaks,
                           exclude_border=exclude_border)
    out = {b: [] for b in images}
    for y, x in peaks:
        c_ref = _centroid(images[ref_band], y, x, half)
        if c_ref is None:
            continue
        for b, img in images.items():
            c = _centroid(img, y, x, half)
            if c is not None:
                out[b].append((c[0] - c_ref[0], c[1] - c_ref[1]))
    return {b: np.array(v).reshape(-1, 2) for b, v in out.items()}


def apply_shift(img, dy, dx):
    """Shift an image by (dy, dx) px (bilinear), keeping NaN regions as NaN.

    To align a band whose stars sit at +offset relative to the reference,
    call apply_shift(img, -dy, -dx).
    """
    from scipy.ndimage import shift as nd_shift
    valid = np.isfinite(img)
    data = nd_shift(np.where(valid, img, 0).astype(np.float32), (dy, dx), order=1, mode="constant", cval=0.0)
    w = nd_shift(valid.astype(np.float32), (dy, dx), order=1, mode="constant", cval=0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = data / w
    return np.where(w > 0.99, out, np.nan).astype(np.float32)
