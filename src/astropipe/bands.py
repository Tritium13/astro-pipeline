"""Filter names and wavelengths (NIRCam and MIRI)."""
import re


def wavelength_um(band: str) -> float:
    """Approximate pivot wavelength in µm from the filter name.

    JWST filter names encode the wavelength in 1/100 µm for both NIRCam
    (F090W -> 0.90 µm) and MIRI (F1130W -> 11.30 µm).
    """
    return int(re.search(r"\d+", band).group()) / 100


def sort_bands(bands):
    """Sort filter names by wavelength (short -> long)."""
    return sorted(bands, key=wavelength_um)


def band_from_header(primary_header) -> str:
    """Filter that defines the passband.

    NIRCam narrow-band filters such as F405N sit in the pupil wheel and are
    combined with a wide filter (FILTER = F444W, PUPIL = F405N); then the
    pupil filter defines the band. MIRI headers have no PUPIL keyword.
    """
    pupil = str(primary_header.get("PUPIL", "CLEAR"))
    if re.fullmatch(r"F\d{3,4}[WMN]2?", pupil):
        return pupil
    return str(primary_header["FILTER"])
