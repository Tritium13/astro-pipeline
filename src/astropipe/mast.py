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


def download(products, dest, max_gb=5.0):
    """Download products flat into `dest`; refuse if larger than `max_gb`."""
    size = total_size_gb(products)
    if max_gb is not None and size > max_gb:
        raise ValueError(f"{size:.2f} GB exceeds max_gb={max_gb}; filter first or raise the limit.")
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    return Observations.download_products(products, download_dir=str(dest), flat=True)
