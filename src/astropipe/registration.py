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
    Existing outputs are reused unless overwrite=True – but only if they were
    made from the same input file (header SRCFILE) and are newer than it;
    otherwise e.g. a later destriping step would silently be ignored.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    for band, path in files_by_band.items():
        out_path = out_dir / f"{prefix}_{band.lower()}_reproj.fits"
        out[band] = out_path
        if out_path.exists() and not overwrite:
            src = fits.getheader(out_path).get("SRCFILE")
            if src == Path(path).name and out_path.stat().st_mtime >= Path(path).stat().st_mtime:
                print(f"{band:<7} exists -> {out_path.name}")
                continue
            print(f"{band:<7} outdated (made from {src}) -> reprojecting")
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


# --- moving targets (planets) -------------------------------------------------
# For TARGTYPE = MOVING the JWST pipeline resamples each i2d in the frame of
# the target: the planet is sharp, the WCS is tied to the target's mean
# position during that exposure (MT_AVRA/MT_AVDEC). Images taken at different
# times therefore have the planet at different sky coordinates. Shifting each
# WCS by the difference of the MT_AV positions puts the planet on the same
# pixels in every filter (background stars then do NOT line up any more).

def moving_target_offsets(files):
    """Per file: (dRA, dDec) in degrees to add to CRVAL so that the target's mean
    position matches that of the first file. Returns {} if not a moving target."""
    pos = {}
    for k, f in files.items():
        h0 = fits.getheader(f, 0)
        h1 = fits.getheader(f, extname="SCI")       # MT_* keywords live in the SCI header
        h = h1 if "MT_AVRA" in h1 else h0
        if h0.get("TARGTYPE") != "MOVING" or "MT_AVRA" not in h:
            return {}
        pos[k] = (h["MT_AVRA"], h["MT_AVDEC"])
    ra0, dec0 = next(iter(pos.values()))
    return {k: (ra0 - ra, dec0 - dec) for k, (ra, dec) in pos.items()}


def write_shifted_i2d(src, dest, d_ra, d_dec, sci=None):
    """Copy PRIMARY + SCI with CRVAL shifted by (d_ra, d_dec) degrees."""
    with fits.open(src, memmap=True) as hdul:
        prim = fits.PrimaryHDU(header=hdul[0].header)
        hdr = hdul["SCI"].header.copy()
        data = hdul["SCI"].data.astype(np.float32) if sci is None else sci
    hdr["CRVAL1"] += d_ra
    hdr["CRVAL2"] += d_dec
    hdr["MTSHIFT1"] = (d_ra * 3600, "[arcsec] RA shift applied to align on target")
    hdr["MTSHIFT2"] = (d_dec * 3600, "[arcsec] Dec shift applied to align on target")
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    fits.HDUList([prim, fits.ImageHDU(data=data, header=hdr, name="SCI")]).writeto(dest, overwrite=True)
    return Path(dest)


def disk_mask(img, frac=0.3, min_px=200, tries=4):
    """Mask of the largest bright connected region (a planet's disk), or None.

    Threshold: frac x the 99.99 % percentile. In a close-up, the 99.99 %
    percentile is set by a few very bright clouds, and the threshold can lie
    above most of the disk (the disk then falls apart into small pieces) –
    so the threshold is halved up to `tries` times until a region of at least
    `min_px` pixels is found. Small bright moons/stars are ignored.
    """
    from scipy import ndimage as ndi
    data = np.nan_to_num(img)
    top = np.percentile(img[np.isfinite(img)], 99.99)
    for i in range(tries):
        lab, n = ndi.label(data > frac * top / 2 ** i)
        if n == 0:
            continue
        sizes = ndi.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
        k = int(np.argmax(sizes)) + 1
        if sizes[k - 1] >= min_px:
            return ndi.binary_fill_holes(lab == k)
    return None


def disk_centroid(img, frac=0.3, min_px=200, ref_mask=None):
    """Geometric centre (y, x) of the planet's disk (unweighted, so bright clouds
    or limb brightening do not pull it).

    ref_mask: disk mask from a reference filter (e.g. F460M, smooth disk, no
    rings). Then the threshold is half the median of this filter inside the
    reference disk – far above the faint rings, which would otherwise merge
    with the disk at low thresholds and pull the centre sideways.
    """
    from scipy import ndimage as ndi
    if ref_mask is None:
        m = disk_mask(img, frac, min_px)
    else:
        data = np.nan_to_num(img)
        lab, n = ndi.label(data > 0.5 * np.nanmedian(img[ref_mask]))
        if n == 0:
            return None
        sizes = ndi.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
        m = ndi.binary_fill_holes(lab == int(np.argmax(sizes)) + 1)
    return None if m is None else ndi.center_of_mass(m)
