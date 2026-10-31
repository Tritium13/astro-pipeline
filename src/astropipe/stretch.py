"""Stage 4: saturated holes, sky background from empty boxes, asinh stretch."""
import numpy as np
from scipy.ndimage import binary_fill_holes, distance_transform_edt, label
from astropy.stats import sigma_clipped_stats


def fill_saturated_holes(img, max_hole_px=2000):
    """Fill NaN regions *inside* the image (saturated star cores) with the image maximum.

    NaN regions connected to the border (empty corners) stay NaN. Holes larger
    than `max_hole_px` are left alone: in mosaics these are usually detector
    gaps, which must not turn white. Returns (filled image, number of filled px).
    """
    img = img.copy()
    finite = np.isfinite(img)
    holes = binary_fill_holes(finite) & ~finite
    if max_hole_px is not None:
        lab, n = label(holes)
        if n:
            sizes = np.bincount(lab.ravel())
            too_big = np.flatnonzero(sizes > max_hole_px)
            too_big = too_big[too_big > 0]
            holes &= ~np.isin(lab, too_big)
    img[holes] = np.nanmax(img)
    return img, int(holes.sum())


def common_valid(images):
    """Pixels that are finite in all bands."""
    return np.logical_and.reduce([np.isfinite(img) for img in images.values()])


def find_sky_boxes(images, valid, box=150, edge_margin=150, n_boxes=6, min_sep=500):
    """Boxes that are dark in all bands, spread over the field.

    Score per candidate box = sum over bands of (box median / 99.9 % percentile).
    Returns (boxes as list of (y, x) lower-left corners, scores).
    """
    inner = distance_transform_edt(valid) > edge_margin
    p999 = {b: np.percentile(img[valid], 99.9) for b, img in images.items()}
    cands = []
    ny, nx = valid.shape
    for y in range(0, ny - box, box // 2):
        for x in range(0, nx - box, box // 2):
            if not inner[y:y + box, x:x + box].all():
                continue
            score = sum(np.median(img[y:y + box, x:x + box]) / p999[b] for b, img in images.items())
            cands.append((float(score), y, x))
    cands.sort()
    boxes, scores = [], []
    for score, y, x in cands:
        if all(np.hypot(y - yy, x - xx) >= min_sep for yy, xx in boxes):
            boxes.append((y, x))
            scores.append(score)
        if len(boxes) == n_boxes:
            break
    return boxes, scores


def sky_stats(images, boxes, box=150):
    """Background (median of box medians), noise (median of box std) and spread per band."""
    stats = {}
    for b, img in images.items():
        meds, stds = [], []
        for y, x in boxes:
            _, med, sd = sigma_clipped_stats(img[y:y + box, x:x + box], sigma=3.0, maxiters=5)
            meds.append(med)
            stds.append(sd)
        stats[b] = dict(bkg=float(np.median(meds)), noise=float(np.median(stds)),
                        spread=float(np.ptp(meds)))
    return stats


def normalize(img, valid, bkg, noise, black_k, white_pct):
    """Map [bkg - black_k*noise, white] -> [0, 1]; invalid pixels -> 0.

    Larger black_k lowers the black point (brighter, noisier background);
    negative black_k hides noise (and the faintest structure).
    """
    x = img - bkg
    black = -black_k * noise
    white = np.percentile(x[valid], white_pct)
    y = np.clip((x - black) / (white - black), 0, 1)
    return np.where(valid, y, 0.0).astype(np.float32), float(black), float(white)


def asinh_stretch(y, a=0.05):
    """asinh(y/a)/asinh(1/a): linear near 0, logarithmic for bright values."""
    return (np.arcsinh(y / a) / np.arcsinh(1 / a)).astype(np.float32)


def stretch_all(images, valid, stats, params):
    """Apply normalize + asinh per band. params: band -> dict(black_k, white_pct, a)."""
    stretched, levels = {}, {}
    for b, img in images.items():
        p = params[b]
        y, black, white = normalize(img, valid, stats[b]["bkg"], stats[b]["noise"],
                                    p["black_k"], p["white_pct"])
        stretched[b] = asinh_stretch(y, p["a"])
        levels[b] = dict(black=black, white=white)
    return stretched, levels
