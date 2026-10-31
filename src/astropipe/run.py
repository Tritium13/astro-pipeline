"""Stage 9.2: run the whole pipeline from a TOML configuration file.

Usage (in the project folder):
    python -m astropipe.run configs/ngc3132.toml
    python -m astropipe.run configs/ngc3132.toml --no-export

Every run writes into data/<run>/ (intermediate files) and output/ (images,
caption), plus params/<run>_run.json with every value that was actually used.
"""
import argparse
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
    obs, prods = mast.find_i2d(d["program"], d["instrument"])
    keep = []
    for i, row in enumerate(prods):
        name = row["productFilename"]
        if d.get("obs") and d["obs"] not in name:
            continue
        if not set(_bands_in_name(name)) & set(d["bands"]):
            continue
        keep.append(i)
    sel = prods[keep]
    log(f"MAST: {len(prods)} i2d products, {len(sel)} selected ({mast.total_size_gb(sel):.2f} GB)")
    mast.download(sel, raw, max_gb=d.get("max_gb", 5.0))
    files = {}
    for name in sel["productFilename"]:
        f = raw / name
        b = bands_mod.band_from_header(fits.getheader(f, 0))
        if b in d["bands"]:
            files[b] = f
    missing = set(d["bands"]) - set(files)
    if missing:
        raise RuntimeError(f"bands not found: {sorted(missing)}")
    return {b: files[b] for b in bands_mod.sort_bands(files)}


# --- step 2: optional destriping ----------------------------------------------

def destripe(cfg, files, work):
    c = cfg.get("clean", {})
    method = c.get("method", "none")
    if method == "none":
        return files, None
    out_dir = work / "cleaned"
    out = dict(files)
    for b in c.get("bands", list(files)):
        dest = out_dir / files[b].name.replace("_i2d", "_destriped_i2d")
        if not dest.exists():
            sci = fits.getdata(files[b], extname="SCI").astype(np.float32)
            if method == "local":
                cleaned, _, _, _ = clean.destripe_local(sci, "rows", block=c.get("block", 16), smooth=c.get("smooth", 51),
                                                        segment=c.get("segment", 512))
            elif method == "sky":
                cleaned, _, _ = clean.destripe(sci, "rows", smooth=c.get("smooth", 51), segment=c.get("segment", 512))
            else:
                raise ValueError(f"unknown clean.method {method!r}")
            clean.write_cleaned_i2d(files[b], dest, cleaned, f"astropipe.run destripe method={method} {c}")
            log(f"destriped {b} ({method})")
        out[b] = dest
    return out, {"method": method, **{k: v for k, v in c.items() if k != "method"}}


# --- step 3: registration ------------------------------------------------------

def register(cfg, files, work, name):
    g = cfg.get("grid", {})
    wcs_out, shape_out = registration.target_grid(files.values(), g.get("resolution_arcsec", 0.063))
    log(f"target grid {shape_out}")
    reproj = registration.reproject_all(files, wcs_out, shape_out, work / "reproj", name)
    imgs = {b: fits.getdata(reproj[b]).astype(np.float32) for b in files}
    ref = list(files)[-1]
    off = registration.star_offsets(imgs, ref)
    offsets = {b: (float(np.median(o)) if o else None) for b, o in off.items()}
    log("star offsets vs %s: %s" % (ref, {b: (round(v, 2) if v is not None else None) for b, v in offsets.items()}))
    return imgs, wcs_out, shape_out, offsets


# --- step 4: background + stretch ---------------------------------------------

def background_and_stretch(cfg, imgs):
    filled = {}
    for b in imgs:
        imgs[b], filled[b] = stretch.fill_saturated_holes(imgs[b], cfg.get("holes", {}).get("max_hole_px", 2000))
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
    stretched, levels = stretch.stretch_all(imgs, valid, stats, params)
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
    center = export.nebula_center(stretched[e.get("center_band", list(stretched)[-1])], valid)
    aspect = e.get("aspect", 1.0)
    half_h, half_w = export.largest_rect(inner, center, aspect=aspect)
    cy, cx = center
    crop = np.s_[cy - half_h:cy + half_h, cx - half_w:cx + half_w]
    north_up, east_left = export.orientation(wcs_out, cy, cx)
    pix = cfg.get("grid", {}).get("resolution_arcsec", 0.063)
    size = (2 * half_w * pix / 60, 2 * half_h * pix / 60)
    rec = {"center_yx": [cy, cx], "half_hw": [half_h, half_w], "size_arcmin": size,
           "north_up": north_up, "east_left": east_left, "files": {}}
    log(f"crop {2 * half_w} x {2 * half_h} px = {size[0]:.2f}' x {size[1]:.2f}'")
    if do_export:
        for vname in e.get("variants", list(rgbs)):
            cap = caption(cfg, vname, size, north_up and east_left, info)
            paths = export.save_outputs(rgbs[vname][crop], cap, f"{name}_{vname}",
                                        root / "output" / "full_res", root / "output" / "runs")
            rec["files"][vname] = [str(p) for p in paths]
            log(f"exported {vname}")
    return rec, crop


def caption(cfg, vname, size, ok_orientation, info):
    c = cfg.get("caption", {})
    v = cfg["color"][vname]
    hues = info["colour"][vname]["hue_deg"]
    rows = "\n".join(f"| {b} | {c.get('colour_names', {}).get(vname, {}).get(b, f'{hues[b]:.0f}°')} | "
                     f"{c.get('filter_content', {}).get(b, '')} |" for b in bands_mod.sort_bands(hues))
    steps = ["calibrated stage-3 images (`_i2d.fits`) from MAST"]
    if info.get("clean"):
        steps.append(f"row destriping ({info['clean']['method']} background model; approximate)")
    steps += [f"common grid {cfg.get('grid', {}).get('resolution_arcsec', 0.063)}″/px (`reproject_adaptive`)",
              "background from sky boxes", "asinh stretch per filter (each normalised to its own white point)",
              "additive colour mixing"]
    if v.get("luminance"):
        steps.append(f"{int(v['luminance'].get('mix', 0.5) * 100)} % of the brightness from {v['luminance']['band']} (LRGB)")
    steps.append("saturated star cores filled with white; no local adjustments")
    orient = "north up, east left" if ok_orientation else "ORIENTATION TO BE CHECKED"
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

    files = fetch(cfg, root)
    info["files"] = {b: f.name for b, f in files.items()}
    files, info["clean"] = destripe(cfg, files, work)
    imgs, wcs_out, shape_out, info["star_offsets_px"] = register(cfg, files, work, name)
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


def main():
    ap = argparse.ArgumentParser(description="Run the astropipe pipeline from a TOML config.")
    ap.add_argument("config")
    ap.add_argument("--no-export", action="store_true", help="skip writing images/captions")
    args = ap.parse_args()
    run(args.config, Path("."), do_export=not args.no_export)


if __name__ == "__main__":
    main()
