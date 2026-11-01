"""Stage 9.2: run the whole pipeline from a TOML configuration file.

Usage (in the project folder):
    python -m astropipe.run configs/ngc3132.toml
    python -m astropipe.run configs/ngc3132.toml --no-export

Every run writes into data/<run>/ (intermediate files) and output/ (images,
caption), plus params/<run>_run.json with every value that was actually used.
"""
import argparse
import hashlib
import json
import re
import time
import tomllib
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
from scipy.ndimage import distance_transform_edt

from . import __version__, bands as bands_mod, clean, color, export, mast, registration, stretch

warnings.simplefilter("ignore", FITSFixedWarning)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_config(path):
    with open(path, "rb") as f:
        return tomllib.load(f)


# --- step 1: data --------------------------------------------------------------

def _bands_in_name(name):
    return [t.upper() for t in re.findall(r"f\d{3,4}[wmn]2?", name.lower())]


def fetch(cfg, root):
    d = cfg["data"]
    raw = root / "data" / d["raw_dir"]
    obs_list = d.get("obs") or []
    obs_list = [obs_list] if isinstance(obs_list, str) else list(obs_list)

    def wanted(name):
        return ((not obs_list or any(o in name for o in obs_list))
                and bool(set(_bands_in_name(name)) & set(d["bands"])))

    # All files already here? Then skip the MAST query (it can be slow or hang).
    local = sorted(f.name for f in raw.glob("*_i2d.fits") if wanted(f.name)) if raw.exists() else []
    have = {(b, o) for n in local for b in _bands_in_name(n) for o in (obs_list or [None])
            if o is None or o in n}
    if local and all((b, o) in have for b in d["bands"] for o in (obs_list or [None])):
        names = local
        log(f"all {len(local)} i2d files present locally – MAST query skipped")
    else:
        obs, prods = mast.find_i2d(d["program"], d["instrument"])
        sel = prods[[i for i, row in enumerate(prods) if wanted(row["productFilename"])]]
        log(f"MAST: {len(prods)} i2d products, {len(sel)} selected ({mast.total_size_gb(sel):.2f} GB)")
        mast.download(sel, raw, max_gb=d.get("max_gb", 5.0))
        names = list(sel["productFilename"])
    # One entry per (band, observation). With a single observation the key is the
    # band itself (as before); with several it is "<band>_<oNNN>" and the
    # observations are combined after reprojection (see `register`).
    files, unit_band = {}, {}
    for name in sorted(names):
        f = raw / name
        b = bands_mod.band_from_header(fits.getheader(f, 0))
        if b not in d["bands"]:
            continue
        key = b
        if len(obs_list) > 1:
            m = re.search(r"[-_](o\d{3})_", name)
            key = f"{b}_{m.group(1) if m else len(files)}"
        files[key], unit_band[key] = f, b
    missing = set(d["bands"]) - set(unit_band.values())
    if missing:
        raise RuntimeError(f"bands not found: {sorted(missing)}")
    order = {b: i for i, b in enumerate(bands_mod.sort_bands(set(unit_band.values())))}
    keys = sorted(files, key=lambda k: (order[unit_band[k]], k))
    return {k: files[k] for k in keys}, unit_band


# --- step 2: optional destriping ----------------------------------------------

def assess_field(files, stripe_thr=0.15, structure_thr=3.0):
    """Measure per band and choose cleaning settings ("clean.method = 'auto'").

    - structure: spread (5–95 %) of a coarse sky model (sources masked, 128-px
      cells) divided by the sky noise. Empty field: only small steps between
      detectors/exposures (≲ 1–2 sigma); a nebula or a large galaxy filling the
      field: many sigma. Median over bands < structure_thr -> empty field.
      (A first criterion, the fraction of "sky" pixels, failed: 0.43–0.51 in a
      clearly empty deep field, because faint galaxies and the stripes themselves
      are masked.)
    - stripes: std of the row/column profile divided by the sky noise (pure
      noise ~ 0.06). Empty field: profile of the empty sky without high-pass;
      extended object: profile of the local residual (else the object's own
      gradient counts as "stripes": NGC 5643 gave 1–6 instead of ~0.1).
    Both thresholds are preliminary (31.10.2026, one field).
    Empty field: sky destriping without high-pass + 2-D background (128 px);
    otherwise: local destriping, no 2-D background.
    """
    meas = {}
    for b, f in files.items():
        sci = fits.getdata(f, extname="SCI").astype(np.float32)
        finite = np.isfinite(sci)
        bg = clean.background_mask(sci)
        v = sci[bg]
        sigma = 1.4826 * float(np.median(np.abs(v - np.median(v)))) if v.size else float("nan")
        model = clean.smooth_model(np.where(bg, sci, np.nan), 128)[finite]
        p5, p95 = np.percentile(model, [5, 95])
        st = {a: clean.stripe_strength(sci, bg, a, smooth=0, segment=512) / sigma for a in ("rows", "columns")}
        lo = {a: clean.stripe_strength_local(sci, axis=a, segment=512) / sigma for a in ("rows", "columns")}
        meas[b] = {"sky_fraction": round(float(bg.sum() / max(finite.sum(), 1)), 3),
                   "structure": round(float((p95 - p5) / sigma), 2),
                   "stripes_sky": {a: round(v, 3) for a, v in st.items()},
                   "stripes_local": {a: round(v, 3) for a, v in lo.items()}}
    empty = float(np.median([m["structure"] for m in meas.values()])) < structure_thr
    log("field type: " + ("empty (compact sources)" if empty else "extended object fills the field"))
    choice = {}
    for b, m in meas.items():
        # empty field: sky profile without high-pass (also catches broad bands);
        # extended object: the sky profile would measure the object itself ->
        # use the local residual (image - 16-px model), as in 08b.
        st = m["stripes_sky"] if empty else m["stripes_local"]
        m["stripes_rows"], m["stripes_columns"] = st["rows"], st["columns"]
        axis = "rows" if m["stripes_rows"] >= m["stripes_columns"] else "columns"
        strong = max(m["stripes_rows"], m["stripes_columns"]) > stripe_thr
        if empty:
            choice[b] = {"method": "sky" if strong else "none", "axis": axis, "smooth": 0, "background2d_cell": 128}
        else:
            choice[b] = {"method": "local" if strong else "none", "axis": axis, "smooth": 51, "background2d_cell": 0}
        log(f"{b}: structure {m['structure']:.1f} sigma, sky {m['sky_fraction']:.2f}, stripes rows {m['stripes_rows']:.2f}"
            f" / columns {m['stripes_columns']:.2f} -> {choice[b]['method']} ({axis}), 2-D bg {choice[b]['background2d_cell']}")
    return {"empty_field": empty, "measured": meas, "chosen": choice}


def destripe(cfg, files, work):
    c = cfg.get("clean", {})
    method = c.get("method", "none")
    if method == "none" and not c.get("background2d_cell", 0):
        return files, None
    rec = {"method": method, **{k: v for k, v in c.items() if k != "method"}}
    if method == "auto":
        rec["auto"] = assess_field(files, c.get("stripe_threshold", 0.15), c.get("structure_threshold", 3.0))
    out_dir = work / "cleaned"
    out = dict(files)
    axes_used = {}
    for b in c.get("bands", list(files)):
        if method == "auto":
            cb = {**c, **rec["auto"]["chosen"][b]}
            if cb["method"] == "none" and not cb["background2d_cell"]:
                continue
        else:
            cb = c
        m = cb["method"]
        dest = out_dir / files[b].name.replace("_i2d", "_destriped_i2d")
        key = hashlib.sha1(json.dumps(cb, sort_keys=True).encode()).hexdigest()[:16]
        fresh = (dest.exists() and dest.stat().st_mtime >= files[b].stat().st_mtime
                 and fits.getheader(dest, extname="SCI").get("ASTCLEAN") == key)
        if not fresh:
            sci = fits.getdata(files[b], extname="SCI").astype(np.float32)
            axis = cb.get("axis", "rows")          # "rows" | "columns" | "auto"
            if axis == "auto":
                s = {a: clean.stripe_strength_local(sci, block=cb.get("block", 16), axis=a) for a in ("rows", "columns")}
                axis = max(s, key=s.get)
                log(f"{b}: stripe strength rows {s['rows']:.3g}, columns {s['columns']:.3g} -> axis {axis}")
                axes_used[b] = {"axis": axis, "strength": s}
            if m == "local":
                cleaned, _, _, _ = clean.destripe_local(sci, axis, block=cb.get("block", 16), smooth=cb.get("smooth", 51),
                                                        segment=cb.get("segment", 512))
            elif m == "sky":
                cleaned, _, _ = clean.destripe(sci, axis, smooth=cb.get("smooth", 51), segment=cb.get("segment", 512))
            elif m == "none":
                cleaned = sci
            else:
                raise ValueError(f"unknown clean.method {m!r}")
            if cb.get("background2d_cell", 0):
                cleaned, _ = clean.subtract_background_2d(cleaned, cell=cb["background2d_cell"])
            clean.write_cleaned_i2d(files[b], dest, cleaned, f"astropipe.run destripe {cb}",
                                    key=("ASTCLEAN", key, "hash of the [clean] settings"))
            log(f"cleaned {b} (destripe {m}, 2-D background cell {cb.get('background2d_cell', 0)})")
        out[b] = dest
    if axes_used:
        rec["auto_axis"] = axes_used
    return out, rec


# --- step 3: registration ------------------------------------------------------

def align_moving_target(cfg, files, work):
    """grid.moving_target = true: shift each WCS so the target (planet) lines up."""
    if not cfg.get("grid", {}).get("moving_target", False):
        return files, None
    offs = registration.moving_target_offsets(files)
    if not offs:
        raise RuntimeError("grid.moving_target = true, but the files are not marked TARGTYPE = MOVING")
    out = {}
    for k, f in files.items():
        dra, ddec = offs[k]
        dest = work / "mt" / f.name.replace(".fits", "_mt.fits")
        if not (dest.exists() and dest.stat().st_mtime >= f.stat().st_mtime):
            registration.write_shifted_i2d(f, dest, dra, ddec)
        out[k] = dest
    log("moving target: WCS shifts [arcsec] " + ", ".join(
        f"{k} ({offs[k][0] * 3600:+.3f}, {offs[k][1] * 3600:+.3f})" for k in files))
    return out, {k: [offs[k][0] * 3600, offs[k][1] * 3600] for k in files}



def combine_observations(parts):
    """Combine several reprojected images of one band (same grid).

    The first image is the reference; every further one is shifted by the
    median difference in the overlap (background offset between observations,
    like skymatch in the JWST pipeline), then all are averaged where they
    overlap. Returns (image, offsets).
    """
    ref = parts[0]
    stack, offsets = [ref], [0.0]
    for p in parts[1:]:
        both = np.isfinite(ref) & np.isfinite(p)
        off = float(np.median(p[both] - ref[both])) if both.sum() > 1000 else 0.0
        stack.append(p - off)
        offsets.append(round(off, 6))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)     # pixels covered by none -> NaN
        img = np.nanmean(np.stack(stack), axis=0).astype(np.float32)
    return img, offsets


def register(cfg, files, work, name, unit_band=None):
    g = cfg.get("grid", {})
    wcs_out, shape_out = registration.target_grid(files.values(), g.get("resolution_arcsec", 0.063),
                                                  g.get("orientation", "north"))
    log(f"target grid {shape_out} ({g.get('orientation', 'north')})")
    reproj = registration.reproject_all(files, wcs_out, shape_out, work / "reproj", name)
    unit_band = unit_band or {k: k for k in files}
    imgs, combined = {}, {}
    for k in files:
        b = unit_band[k]
        imgs.setdefault(b, []).append(fits.getdata(reproj[k]).astype(np.float32))
    for b, parts in imgs.items():
        if len(parts) == 1:
            imgs[b] = parts[0]
        else:
            imgs[b], offs = combine_observations(parts)
            combined[b] = {"units": [k for k in files if unit_band[k] == b], "offsets": offs}
            log(f"{b}: combined {len(parts)} observations, background offsets {offs}")
    if combined:
        cfg.setdefault("_combined", combined)
    ref = list(imgs)[-1]
    if g.get("moving_target", False):
        ref_disk = registration.disk_mask(imgs[ref])
        cen = {b: registration.disk_centroid(im, ref_mask=ref_disk) for b, im in imgs.items()}
        y0, x0 = cen[ref]
        offsets = {b: (float(np.hypot(c[0] - y0, c[1] - x0)) if c else None) for b, c in cen.items()}
        log("planet disk centroid offsets vs %s [px]: %s" % (ref, {b: (round(v, 2) if v is not None else None)
                                                                   for b, v in offsets.items()}))
        cfg["_disk_centre_yx"] = [float(y0), float(x0)]
        return imgs, wcs_out, shape_out, offsets
    off = registration.star_offsets(imgs, ref)
    offsets = {b: (float(np.median(o)) if o else None) for b, o in off.items()}
    log("star offsets vs %s: %s" % (ref, {b: (round(v, 2) if v is not None else None) for b, v in offsets.items()}))
    return imgs, wcs_out, shape_out, offsets


# --- step 4: background + stretch ---------------------------------------------

def background_and_stretch(cfg, imgs):
    filled = {}
    h = cfg.get("holes", {})
    sat_union = None
    for b in imgs:
        before = ~np.isfinite(imgs[b])
        imgs[b], n_sat, n_bad = stretch.fill_holes(imgs[b], h.get("max_hole_px", 2000),
                                                   k_sigma=h.get("k_sigma", 20.0), min_ratio=h.get("min_ratio", 1.5))
        filled[b] = {"saturated_px": n_sat, "bad_px": n_bad}
        if h.get("unify_saturated", False):
            sat = before & (imgs[b] == np.nanmax(imgs[b]))
            sat_union = sat if sat_union is None else (sat_union | sat)
    log("filled holes (saturated / bad px): " + ", ".join(f"{b} {v['saturated_px']}/{v['bad_px']}" for b, v in filled.items()
                                                         if isinstance(v, dict)))
    valid = stretch.common_valid(imgs)
    bg = cfg.get("background", {})
    box = bg.get("box", 150)
    if "boxes_yx" in bg:
        boxes, scores = [tuple(b) for b in bg["boxes_yx"]], None
    else:
        boxes, scores = stretch.find_sky_boxes(imgs, valid, box, bg.get("edge_margin", 150),
                                               bg.get("n_boxes", 6), bg.get("min_sep", 500))
        if bg.get("drop_negative", True):
            boxes = [bx for bx, s in zip(boxes, scores) if s > 0]
    log(f"{len(boxes)} sky boxes")
    stats = stretch.sky_stats(imgs, boxes, box)
    st = cfg.get("stretch", {})
    default = {k: st.get(k, v) for k, v in dict(black_k=1.0, white_pct=99.9, a=0.05).items()}
    params = {b: {**default, **st.get("bands", {}).get(b, {})} for b in imgs}
    if st.get("white_region") == "planet":
        # white point from the planet's disk instead of the whole field: the disk
        # is a tiny fraction of the pixels, a field percentile would burn it out
        ref = list(imgs)[-1]
        disk = registration.disk_mask(imgs[ref])
        for b in imgs:
            x = imgs[b] - stats[b]["bkg"]
            params[b]["white_value"] = float(np.percentile(x[disk & valid], params[b].get("white_pct_disk",
                                                                                     st.get("white_pct_disk", 99.0))))
    stretched, levels = stretch.stretch_all(imgs, valid, stats, params)
    if sat_union is not None:
        # saturated in any filter -> white in all (otherwise coloured blocks where
        # the saturated areas differ between filters); cosmetic
        for b in stretched:
            stretched[b][sat_union] = 1.0
        filled["unified_saturated_px"] = int(sat_union.sum())
    rec = {"saturated_holes_filled_px": filled, "sky_boxes": {"size_px": box, "yx": [list(map(int, b)) for b in boxes],
           "scores": scores}, "per_band": {b: {**params[b], **stats[b], **levels[b]} for b in imgs}}
    return stretched, valid, rec


# --- step 5: colour ------------------------------------------------------------

def make_colours(cfg, stretched):
    out, rec = {}, {}
    for vname, v in cfg["color"].items():
        if v.get("mode") == "chromatic":
            hues = {b: 240 - i * 240 / max(1, len(stretched) - 1) for i, b in enumerate(bands_mod.sort_bands(stretched))}
        else:
            hues = v["hue_deg"]
        mapping = color.mapping_from_degrees(hues, v.get("saturation", {}))
        rgb = color.compose(stretched, mapping, v.get("weights", {}))
        if "luminance" in v:
            rgb = color.apply_luminance(rgb, stretched[v["luminance"]["band"]], v["luminance"].get("mix", 0.5))
        out[vname] = rgb
        rec[vname] = {"hue_deg": hues, "saturation": v.get("saturation", {}), "weights": v.get("weights", {}),
                      "luminance": v.get("luminance")}
    return out, rec


# --- step 6: crop + export -----------------------------------------------------

def crop_and_export(cfg, rgbs, stretched, valid, wcs_out, name, root, info, do_export=True):
    e = cfg.get("export", {})
    inner = distance_transform_edt(valid) > e.get("margin", 120)
    aspect = e.get("aspect", 1.0)
    mode = e.get("center", "auto")          # "content" | "nebula" | "interior" | "auto" | [y, x] | "planet"
    center, used, bright = None, mode, None
    if mode == "planet":                     # centre of the planet's disk (grid.moving_target)
        mode = [round(v) for v in cfg["_disk_centre_yx"]]
    if isinstance(mode, (list, tuple)):     # hand-set centre [y, x] in grid pixels (see *_overview.jpg)
        cy, cx = (int(v) for v in mode)
        if "size_px" in e:                  # explicit size; may include gaps (shown black)
            h, w = (e["size_px"], e["size_px"]) if isinstance(e["size_px"], int) else e["size_px"]
            half_h, half_w = h // 2, w // 2
        else:
            half_h, half_w = export.largest_rect(inner, (cy, cx), aspect=aspect)
        center, used = (cy, cx), ("planet" if e.get("center") == "planet" else "manual")
    elif mode == "max":                      # largest rectangle inside the valid area (any aspect ratio)
        center, (half_h, half_w) = export.max_rect(inner)
        used = "max"
    elif mode == "content":                  # crop position, size and aspect from the image content
        center, (half_h, half_w), asp = export.content_crop(inner, list(stretched.values()),
                                                            beta=e.get("content_beta", 1.0))
        used = f"content (aspect {asp:.2f})"
    elif mode in ("nebula", "auto"):
        center = export.nebula_center(stretched[e.get("center_band", list(stretched)[-1])], valid)
        bright = [int(v) for v in center]
        try:
            half_h, half_w = export.largest_rect(inner, center, aspect=aspect)
            used = "nebula"
        except ValueError:
            if mode == "nebula":
                raise
            log(f"no crop fits around the brightness centre {center} -> using the interior centre")
            center = None
    if center is None:
        center = export.interior_center(valid)
        half_h, half_w = export.largest_rect(inner, center, aspect=aspect)
        used = "interior"
    cy, cx = center
    crop = np.s_[cy - half_h:cy + half_h, cx - half_w:cx + half_w]
    north_up, east_left = export.orientation(wcs_out, cy, cx)
    nang = export.north_angle(wcs_out, cy, cx)
    if north_up and east_left and abs(nang) < 0.5:
        orient = "north up, east left"
    elif east_left or abs(nang) >= 0.5:
        orient = (f"rotated to the field: north points {abs(nang):.0f}° "
                  f"{'counter-clockwise' if nang > 0 else 'clockwise'} from up")
    else:
        orient = "ORIENTATION TO BE CHECKED"
    pix = cfg.get("grid", {}).get("resolution_arcsec", 0.063)
    size = (2 * half_w * pix / 60, 2 * half_h * pix / 60)
    rec = {"center_mode": used, "center_yx": [cy, cx], "half_hw": [half_h, half_w], "size_arcmin": size,
           "brightness_center_yx": bright, "north_up": north_up, "east_left": east_left,
           "north_angle_deg": round(nang, 2), "files": {}}
    log(f"crop {2 * half_w} x {2 * half_h} px = {size[0]:.2f}' x {size[1]:.2f}'")
    if do_export:
        for vname in e.get("variants", list(rgbs)):
            cap = caption(cfg, vname, size, orient, info, used)
            paths = export.save_outputs(rgbs[vname][crop], cap, f"{name}_{vname}",
                                        root / "output" / "full_res", root / "output" / "runs")
            ov = export.save_overview(rgbs[vname], root / "output" / "runs" / f"{name}_{vname}_overview.jpg",
                                      crop=crop, marker=bright)
            rec["files"][vname] = [str(p) for p in paths] + [str(ov)]
            if e.get("full_field", True):       # additionally the whole observed field (bounding box of valid data)
                rows, cols = np.nonzero(valid.any(axis=1))[0], np.nonzero(valid.any(axis=0))[0]
                fcrop = np.s_[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
                fsize = ((cols[-1] + 1 - cols[0]) * pix / 60, (rows[-1] + 1 - rows[0]) * pix / 60)
                fcap = caption(cfg, vname, fsize, orient, info, "full field") + \
                    "\nFull observed field (not cropped); areas without data are black.\n"
                fpaths = export.save_outputs(rgbs[vname][fcrop], fcap, f"{name}_{vname}_field",
                                             root / "output" / "full_res", root / "output" / "runs", web_max=3000)
                rec["files"][vname] += [str(p) for p in fpaths]
            log(f"exported {vname} (+ overview" + (", full field)" if e.get("full_field", True) else ")"))
    return rec, crop


def caption(cfg, vname, size, orient, info, crop_mode=None):
    c = cfg.get("caption", {})
    v = cfg["color"][vname]
    hues = info["colour"][vname]["hue_deg"]
    rows = "\n".join(f"| {b} | {c.get('colour_names', {}).get(vname, {}).get(b, f'{hues[b]:.0f}°')} | "
                     f"{c.get('filter_content', {}).get(b, '')} |" for b in bands_mod.sort_bands(hues))
    steps = ["calibrated stage-3 images (`_i2d.fits`) from MAST"]
    cl = info.get("clean") or {}
    chosen = (cl.get("auto") or {}).get("chosen")
    applied = ([m["method"] for m in chosen.values() if m.get("method") != "none"] if chosen
               else ([cl["method"]] if cl.get("method") not in (None, "none") else []))
    if applied:
        steps.append(f"row destriping ({', '.join(sorted(set(applied)))} background model; approximate)")
    rot = " rotated to the field" if cfg.get("grid", {}).get("orientation") == "field" else ""
    steps += [f"common grid{rot} {cfg.get('grid', {}).get('resolution_arcsec', 0.063)}″/px (`reproject_adaptive`)",
              "background from sky boxes", "asinh stretch per filter (each normalised to its own white point)",
              "additive colour mixing"]
    if v.get("luminance"):
        steps.append(f"{int(v['luminance'].get('mix', 0.5) * 100)} % of the brightness from {v['luminance']['band']} (LRGB)")
    steps.append("saturated star cores filled with white, isolated bad pixels with the local median; no local adjustments")
    if crop_mode:
        steps.append({"manual": "crop set by hand", "full field": "full observed field, not cropped",
                      "max": "crop = largest rectangle inside the observed area"}.get(
                          crop_mode, f"crop chosen automatically ({crop_mode})"))
    return f"""# {c.get('title', cfg['run']['name'])}

{c.get('description', '')} Field of view ≈ {size[0]:.1f} × {size[1]:.1f} arcmin, {orient}.

## Colour assignment ({vname}: {v.get('label', '')})

| Filter | Colour | Mainly traces |
|---|---|---|
{rows}

{c.get('filter_source', '')} The recorded light is infrared; all colours are an assignment, not "true" colours.

## Processing

{' → '.join(steps)}. Generated by `astropipe.run` (astropipe {__version__}) from `{info['config']}`; all values in `params/{cfg['run']['name']}_run.json`.

## Credits

{c.get('credits', '')}
"""


# --- main ----------------------------------------------------------------------

def run(config_path, root=Path("."), do_export=True):
    t0 = time.perf_counter()
    root = Path(root)
    cfg = load_config(config_path)
    name = cfg["run"]["name"]
    work = root / "data" / f"{name}_run"
    work.mkdir(parents=True, exist_ok=True)
    try:
        rel = Path(config_path).resolve().relative_to(root.resolve())
    except ValueError:
        rel = Path(config_path)
    info = {"config": str(rel), "astropipe": __version__}

    files, unit_band = fetch(cfg, root)
    info["files"] = {b: f.name for b, f in files.items()}
    files, info["clean"] = destripe(cfg, files, work)
    files, info["moving_target"] = align_moving_target(cfg, files, work)
    imgs, wcs_out, shape_out, info["star_offsets_px"] = register(cfg, files, work, name, unit_band)
    if cfg.get("_disk_centre_yx"):
        info["planet_centre_yx"] = cfg["_disk_centre_yx"]
    if cfg.get("_combined"):
        info["combined"] = cfg.pop("_combined")
    info["grid_shape"] = [int(v) for v in shape_out]
    stretched, valid, info["stretch"] = background_and_stretch(cfg, imgs)
    for b, s in stretched.items():
        fits.writeto(work / f"{name}_{b.lower()}_stretched.fits", s, overwrite=True)
    rgbs, info["colour"] = make_colours(cfg, stretched)
    for vname, rgb in rgbs.items():
        np.save(work / f"{name}_{vname}.npy", rgb)
    info["export"], _ = crop_and_export(cfg, rgbs, stretched, valid, wcs_out, name, root, info, do_export)
    info["runtime_s"] = round(time.perf_counter() - t0, 1)
    (root / "params" / f"{name}_run.json").write_text(json.dumps(info, indent=2, default=float))
    log(f"done in {info['runtime_s']} s -> params/{name}_run.json")
    return info


def open_result(info):
    """Open the exported web JPEG(s) in the system image viewer (macOS: `open`, Linux: `xdg-open`)."""
    import shutil
    import subprocess
    import sys
    files = [p for v in info.get("export", {}).get("files", {}).values() for p in v
             if str(p).endswith("_web.jpg") and not str(p).endswith("_field_web.jpg")]   # the crop, not the full field
    cmd = "open" if sys.platform == "darwin" else ("xdg-open" if shutil.which("xdg-open") else None)
    if files and cmd:
        for p in files:
            subprocess.run([cmd, str(p)], check=False)


def main():
    ap = argparse.ArgumentParser(description="Run the astropipe pipeline from a TOML config.")
    ap.add_argument("config")
    ap.add_argument("--no-export", action="store_true", help="skip writing images/captions")
    ap.add_argument("--no-open", action="store_true", help="do not open the finished image")
    args = ap.parse_args()
    info = run(args.config, Path("."), do_export=not args.no_export)
    if not args.no_export and not args.no_open:
        open_result(info)


if __name__ == "__main__":
    main()
