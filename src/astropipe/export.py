"""Stage 6: crop, orientation check and file export."""
from pathlib import Path

import numpy as np


def nebula_center(img, valid, power=4):
    """Brightness-weighted centre (y, x); `power` emphasises the brightest regions."""
    w = np.where(valid, img, 0).astype(np.float64) ** power
    yy, xx = np.indices(w.shape)
    return int(round((w * yy).sum() / w.sum())), int(round((w * xx).sum() / w.sum()))


def interior_center(valid):
    """Pixel (y, x) farthest from any invalid pixel – the 'most interior' point.

    Robust for arbitrary fields (galaxies at the edge, module gaps), where a
    brightness-weighted centre can fall outside the usable area.
    """
    from scipy.ndimage import distance_transform_edt
    d = distance_transform_edt(valid)
    y, x = np.unravel_index(np.argmax(d), d.shape)
    return int(y), int(x)


def largest_square(inner, center, min_half=50):
    """Largest half-size h such that the square centred on `center` lies inside `inner`."""
    cy, cx = center

    def ok(h):
        if cy - h < 0 or cx - h < 0 or cy + h > inner.shape[0] or cx + h > inner.shape[1]:
            return False
        return bool(inner[cy - h:cy + h, cx - h:cx + h].all())

    lo, hi = min_half, max(inner.shape)
    if not ok(lo):
        raise ValueError("Not even the minimum square fits – check centre/margin.")
    while lo < hi:
        mid = (lo + hi + 1) // 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid - 1)
    return lo


def largest_rect(inner, center, aspect=1.0, min_half=50):
    """Largest rectangle (half-height h, half-width round(aspect*h)) centred on `center`
    inside `inner`. aspect = width / height, e.g. 4/3 for landscape."""
    cy, cx = center

    def ok(h):
        w = int(round(aspect * h))
        if cy - h < 0 or cx - w < 0 or cy + h > inner.shape[0] or cx + w > inner.shape[1]:
            return False
        return bool(inner[cy - h:cy + h, cx - w:cx + w].all())

    lo, hi = min_half, max(inner.shape)
    if not ok(lo):
        raise ValueError("Not even the minimum rectangle fits – check centre/margin/aspect.")
    while lo < hi:
        mid = (lo + hi + 1) // 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid - 1)
    return lo, int(round(aspect * lo))


CONTENT_ASPECTS = (2 / 5, 1 / 2, 9 / 16, 3 / 4, 1.0, 4 / 3, 16 / 9, 2.0, 5 / 2)


def _block(a, f, func):
    """Reduce a 2-D array in f x f blocks (edges trimmed)."""
    h, w = (a.shape[0] // f) * f, (a.shape[1] // f) * f
    return func(a[:h, :w].reshape(h // f, f, w // f, f), axis=(1, 3))


def content_crop(inner, layers, aspects=CONTENT_ASPECTS, sizes=None, max_px=600, box=5, ring=3, beta=1.0):
    """Choose crop centre, size and aspect ratio from the image content.

    Works on a downsampled copy (longest side ~max_px blocks; block *median*, so single stars
    and diffraction spikes count little). 'Content' = local contrast (standard deviation in
    box x box blocks: filaments, pillar edges, clusters) + brightness above the typical sky
    (extended objects such as galaxies), both normalised to their mean. For every aspect
    ratio the largest crop that fits completely inside `inner` is found; then sizes from
    30 to 100 % of it are tried at
    every position. Score = contrast inside the crop minus `beta` x (contrast in the outer
    band of `ring` blocks, scaled to the crop area): rich inside, calm along the border, so
    the crop tends not to cut through the motif. Returns ((cy, cx), (half_h, half_w), aspect).
    """
    from scipy.ndimage import uniform_filter
    sizes = np.arange(0.3, 1.001, 0.05) if sizes is None else sizes
    f = max(1, int(np.ceil(max(inner.shape) / max_px)))
    ok = _block(inner, f, np.all)
    def bmedian(b, axis):
        return np.median(b.transpose(0, 2, 1, 3).reshape(b.shape[0], b.shape[2], -1), axis=-1)

    lum = np.mean([_block(np.nan_to_num(np.asarray(x, dtype=np.float32)), f, bmedian) for x in layers], axis=0)
    m, m2 = uniform_filter(lum, box), uniform_filter(lum * lum, box)
    contrast = np.sqrt(np.clip(m2 - m * m, 0, None))
    excess = np.clip(lum - np.median(lum[ok]), 0, None) if ok.any() else np.zeros_like(lum)
    sal = contrast / (contrast[ok].mean() + 1e-12) + excess / (excess[ok].mean() + 1e-12)
    sal[~ok] = 0
    bad = np.pad((~ok).astype(np.int64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    S = np.pad(sal.astype(np.float64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))

    def win(I, h, w):                       # sums over all h x w windows (integral image)
        return I[h:, w:] - I[:-h, w:] - I[h:, :-w] + I[:-h, :-w]

    H, W = ok.shape
    best = (-np.inf,)
    for asp in aspects:
        def fits(h):
            w = int(round(asp * h))
            return 1 <= w <= W and h <= H and bool((win(bad, h, w) == 0).any())
        lo, hi = 0, H
        while lo < hi:
            mid = (lo + hi + 1) // 2
            lo, hi = (mid, hi) if fits(mid) else (lo, mid - 1)
        for sz in sizes:
            h = int(sz * lo)
            w = int(round(asp * h))
            if h < 4 * ring or w < 4 * ring:
                continue
            inside = win(S, h, w)
            core = win(S, h - 2 * ring, w - 2 * ring)[ring:ring + inside.shape[0], ring:ring + inside.shape[1]]
            n_in, n_edge = h * w, h * w - (h - 2 * ring) * (w - 2 * ring)
            score = np.where(win(bad, h, w) == 0, inside - beta * (inside - core) * n_in / n_edge, -np.inf)
            k = int(np.argmax(score))
            if score.flat[k] > best[0]:
                y0, x0 = np.unravel_index(k, score.shape)
                best = (score.flat[k], asp, h, w, y0, x0)
    if best[0] == -np.inf:
        raise ValueError("no crop fits inside the valid area")
    _, asp, h, w, y0, x0 = best
    return (int((y0 + h / 2) * f), int((x0 + w / 2) * f)), (h * f // 2, w * f // 2), float(asp)


def north_angle(wcs, cy, cx):
    """Direction of north in the image at pixel (cy, cx): degrees from 'up', counter-clockwise positive."""
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    c0 = wcs.pixel_to_world(cx, cy)
    n = SkyCoord(c0.ra, c0.dec + 2 * u.arcsec, frame=c0.frame)
    x1, y1 = wcs.world_to_pixel(n)
    return float(np.degrees(np.arctan2(-(x1 - cx), y1 - cy)))


def max_rect(inner, max_px=1200):
    """Largest axis-parallel rectangle completely inside `inner` (any aspect ratio).

    Row-by-row histogram + stack method on a block-downsampled mask (block = all valid).
    Returns ((cy, cx), (half_h, half_w)).
    """
    f = max(1, int(np.ceil(max(inner.shape) / max_px)))
    ok = _block(inner, f, np.all)
    H, W = ok.shape
    heights = np.zeros(W, dtype=np.int64)
    best = (0, 0, 0, 0, 0)                     # area, last row, left column, height, width
    for r in range(H):
        heights = np.where(ok[r], heights + 1, 0)
        stack = []
        for c in range(W + 1):
            hc = int(heights[c]) if c < W else 0
            start = c
            while stack and stack[-1][1] >= hc:
                s0, hs = stack.pop()
                if hs * (c - s0) > best[0]:
                    best = (hs * (c - s0), r, s0, hs, c - s0)
                start = s0
            stack.append((start, hc))
    if best[0] == 0:
        raise ValueError("no rectangle fits inside the valid area")
    _, r, s0, h, w = best
    y0 = r - h + 1
    return (int((y0 + h / 2) * f), int((s0 + w / 2) * f)), (h * f // 2, w * f // 2)


def orientation(wcs, cy, cx, step=100):
    """(north_up, east_left) at pixel (cy, cx), checked with the WCS."""
    c0 = wcs.pixel_to_world(cx, cy)
    up = wcs.pixel_to_world(cx, cy + step)
    left = wcs.pixel_to_world(cx - step, cy)
    north_up = bool(up.dec > c0.dec)
    east_left = bool((left.ra - c0.ra).wrap_at("180d").deg > 0)
    return north_up, east_left


TO_ASCII = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss",
                          "′": "'", "″": '"', "≈": "~", "×": "x", "→": "->", "α": "alpha", "₂": "2",
                          "„": '"', "“": '"', "”": '"', "–": "-", "—": "-"})


def to_ascii(text):
    """TIFF descriptions must be 7-bit ASCII; unknown characters become '?'."""
    return text.translate(TO_ASCII).encode("ascii", "replace").decode("ascii")


def save_outputs(rgb, caption, stem, full_dir, web_dir, web_max=2000, jpeg_quality=92):
    """Write 16-bit TIFF + full PNG (full_dir) and web JPEG + caption .md (web_dir).

    `rgb` is a float image (0–1) with origin='lower' (row 0 = bottom); it is
    flipped so that north is up in the files.
    """
    import tifffile
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo

    full_dir, web_dir = Path(full_dir), Path(web_dir)
    full_dir.mkdir(parents=True, exist_ok=True)
    web_dir.mkdir(parents=True, exist_ok=True)
    final = np.flipud(np.clip(rgb, 0, 1))

    paths = [full_dir / f"{stem}_16bit.tif", full_dir / f"{stem}_full.png",
             web_dir / f"{stem}_web.jpg", web_dir / f"{stem}_caption.md"]
    tifffile.imwrite(paths[0], (final * 65535 + 0.5).astype(np.uint16),
                     photometric="rgb", description=to_ascii(caption))
    img8 = Image.fromarray((final * 255 + 0.5).astype(np.uint8))
    info = PngInfo()
    info.add_text("Description", caption)
    img8.save(paths[1], pnginfo=info)
    web = img8.copy()
    web.thumbnail((web_max, web_max), Image.Resampling.LANCZOS)
    web.save(paths[2], quality=jpeg_quality)
    paths[3].write_text(caption, encoding="utf-8")
    return paths


def save_overview(rgb, path, crop=None, marker=None, max_px=1500, jpeg_quality=90):
    """Downscaled JPEG of the whole field with the crop drawn as a frame.

    `rgb` (origin='lower') covers the full grid; `crop` is the (y, x) slice pair
    used for the export, `marker` an optional (y, x) point (e.g. brightness
    centre). Both are given in grid pixels and drawn north up like the export.
    """
    from PIL import Image, ImageDraw

    h, w = rgb.shape[:2]
    img = Image.fromarray((np.flipud(np.clip(rgb, 0, 1)) * 255 + 0.5).astype(np.uint8))
    scale = min(1.0, max_px / max(h, w))
    img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(img)
    lw = max(2, round(3 * img.width / 1500))

    def xy(y, x):                     # grid (origin lower) -> image (origin upper)
        return x * scale, (h - y) * scale

    if crop is not None:
        ys, xs = crop
        x0, y0 = xy(ys.start, xs.start)
        x1, y1 = xy(ys.stop, xs.stop)
        draw.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], outline=(255, 255, 255), width=lw)
    if marker is not None:
        mx, my = xy(*marker)
        r = 6 * lw
        draw.line([mx - r, my, mx + r, my], fill=(255, 60, 60), width=lw)
        draw.line([mx, my - r, mx, my + r], fill=(255, 60, 60), width=lw)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save(path, quality=jpeg_quality)
    return Path(path)
