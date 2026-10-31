"""Stage 6: crop, orientation check and file export."""
from pathlib import Path

import numpy as np


def nebula_center(img, valid, power=4):
    """Brightness-weighted centre (y, x); `power` emphasises the brightest regions."""
    w = np.where(valid, img, 0).astype(np.float64) ** power
    yy, xx = np.indices(w.shape)
    return int(round((w * yy).sum() / w.sum())), int(round((w * xx).sum() / w.sum()))


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
