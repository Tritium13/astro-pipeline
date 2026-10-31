"""Stage 4: saturated holes, sky background from empty boxes, asinh stretch."""
import numpy as np
from scipy.ndimage import binary_dilation, binary_fill_holes, distance_transform_edt, find_objects, label
from astropy.stats import sigma_clipped_stats


def classify_holes(img, max_hole_px=2000, ring_px=2, ann_in=6, ann_out=10, k_sigma=20.0, min_ratio=1.5):
    """Find NaN holes inside the image and classify them by *local* contrast.

    For every hole: median of an inner ring (1..ring_px px around it) vs. an
    outer annulus (ann_in..ann_out px). A saturated star core sits on the
    steep wings of the star, so the inner ring is much brighter than the
    annulus; a bad/flagged pixel has similar values all around – on dark sky
    as well as on bright nebula (a global brightness threshold fails there).

    saturated  <=>  ring - annulus > k_sigma * sigma  and  ring > min_ratio * annulus
    (sigma = robust noise of the whole image). Holes larger than `max_hole_px`
    (detector/module gaps) are skipped. Returns (label image, list of dicts).
    """
    finite = np.isfinite(img)
    holes = binary_fill_holes(finite) & ~finite
    lab, n = label(holes)
    if n == 0:
        return lab, []
    v = img[finite]
    sigma = 1.4826 * np.median(np.abs(v - np.median(v)))
    sizes = np.bincount(lab.ravel())
    pad = ann_out + 1
    out = []
    for i, sl in enumerate(find_objects(lab), start=1):
        if sl is None or sizes[i] > max_hole_px:
            continue
        y0, y1 = max(sl[0].start - pad, 0), sl[0].stop + pad
        x0, x1 = max(sl[1].start - pad, 0), sl[1].stop + pad
        sub = img[y0:y1, x0:x1]
        comp = lab[y0:y1, x0:x1] == i
        ok = np.isfinite(sub)
        d1 = binary_dilation(comp, iterations=ring_px)
        d_in = binary_dilation(comp, iterations=ann_in)
        d_out = binary_dilation(comp, iterations=ann_out)
        ring, ann = d1 & ~comp & ok, d_out & ~d_in & ok
        r = float(np.median(sub[ring])) if ring.any() else np.nan
        a = float(np.median(sub[ann])) if ann.any() else np.nan
        sat = bool(np.isfinite(r) and np.isfinite(a) and (r - a) > k_sigma * sigma
                   and (a <= 0 or r > min_ratio * a))
        cy, cx = (sl[0].start + sl[0].stop) // 2, (sl[1].start + sl[1].stop) // 2
        out.append(dict(label=i, size=int(sizes[i]), yx=(int(cy), int(cx)), ring=r, annulus=a,
                        saturated=sat, box=(y0, y1, x0, x1)))
    return lab, out


def fill_holes(img, max_hole_px=2000, **kw):
    """Fill classified holes: saturated -> image maximum (white), bad pixel -> ring median.

    Returns (filled image, n_saturated_px, n_bad_px). See classify_holes().
    """
    img = img.copy()
    lab, holes = classify_holes(img, max_hole_px, **kw)
    vmax = np.nanmax(img)
    fallback = np.nanmedian(img)
    n_sat = n_bad = 0
    for h in holes:
        y0, y1, x0, x1 = h["box"]
        sub = img[y0:y1, x0:x1]
        comp = lab[y0:y1, x0:x1] == h["label"]
        if h["saturated"]:
            sub[comp] = vmax
            n_sat += h["size"]
        else:
            sub[comp] = h["ring"] if np.isfinite(h["ring"]) else fallback
            n_bad += h["size"]
    return img, n_sat, n_bad


def fill_saturated_holes(img, max_hole_px=2000, **kw):
    """Compatibility wrapper around fill_holes(): returns (filled, total filled px)."""
    out, n_sat, n_bad = fill_holes(img, max_hole_px, **kw)
    return out, n_sat + n_bad


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
