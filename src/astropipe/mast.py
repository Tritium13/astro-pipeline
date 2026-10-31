"""Stage 1: find and download calibrated stage-3 images (i2d) from MAST."""
from pathlib import Path

from astroquery.mast import Observations


def find_i2d(program, instrument="NIRCAM/IMAGE"):
    """Return (observations, i2d products) for a JWST programme and instrument."""
    obs = Observations.query_criteria(
        obs_collection="JWST",
        proposal_id=str(program),
        instrument_name=instrument,
        calib_level=3,
    )
    if len(obs) == 0:
        return obs, obs
    products = Observations.get_product_list(obs)
    i2d = Observations.filter_products(
        products,
        productType="SCIENCE",
        productSubGroupDescription="I2D",
        calib_level=[3],
    )
    return obs, i2d


def total_size_gb(products) -> float:
    return float(products["size"].sum()) / 1e9


def missing_products(products, dest):
    """Products that are not yet in `dest` with the expected size (MAST `size` column).

    MAST's size column can differ by a few kB from the delivered file
    (seen for NGC 3132), so a relative tolerance of 1 % is used.
    """
    dest = Path(dest)
    keep = []
    for i, row in enumerate(products):
        f = dest / row["productFilename"]
        if not (f.exists() and abs(f.stat().st_size - int(row["size"])) <= 0.01 * int(row["size"])):
            keep.append(i)
    return products[keep]


def download(products, dest, max_gb=5.0):
    """Download products flat into `dest`, skipping files that are already there.

    Refuses if the *missing* part is larger than `max_gb`.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    todo = missing_products(products, dest)
    print(f"{len(products) - len(todo)} of {len(products)} files already present, "
          f"{len(todo)} to download ({total_size_gb(todo):.2f} GB)")
    if len(todo) == 0:
        return None
    size = total_size_gb(todo)
    if max_gb is not None and size > max_gb:
        raise ValueError(f"{size:.2f} GB exceeds max_gb={max_gb}; filter first or raise the limit.")
    return Observations.download_products(todo, download_dir=str(dest), flat=True)
