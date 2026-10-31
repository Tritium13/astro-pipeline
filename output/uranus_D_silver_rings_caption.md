# Uranus – JWST NIRCam

Uranus, observed on 2025-02-02 with NIRCam on the James Webb Space Telescope (programme 6379). Field of view ≈ 20″ × 20″, north up, east left. Filters taken at slightly different times were aligned on the planet.

## Colour assignment (D_silver_rings: chosen freely: cool disk from four filters, F356W laid over as white light (rings silver))

| Filter | Hue |
|---|---|
| F115W | 185° |
| F150W | 195° |
| F277W | 205° |
| F444W | 215° |

The recorded light is infrared; all colours are an assignment, not "true" colours.

## Processing

calibrated stage-3 images (`_i2d.fits`) from MAST → F070W not used (planet's disk saturated) → row destriping on empty sky (no high-pass) → aligned on the planet (WCS shifted by the target's mean positions, header MT_AVRA/MT_AVDEC) → close-up grid 0.031″/px centred on Uranus (`reproject_adaptive`; long-wavelength filters upsampled ×2) → background from empty corners → asinh stretch (a = 0.02), white point from the disk (99.5 %), for F356W from the brightest field pixels (rings), each filter normalised to its own white point → additive colour mixing, 50 % of the brightness from F150W (LRGB), F356W laid over as white light (strength 0.9) → bad pixels filled with the local median, saturated features with the local maximum, white in all filters where saturated in any; no local adjustments. Notebook `13_uranus.ipynb`; all values in `params/uranus.json`.

## Credits

Data: NASA, ESA, CSA, STScI (programme 6379), retrieved via MAST. Processing: Tritium13.
