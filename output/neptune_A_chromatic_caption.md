# Neptune – JWST NIRCam

Neptune and its rings, observed on 12 July 2022 with NIRCam on the James Webb Space Telescope (programme 2739). Field of view ≈ 14″ × 14″, north up, east left. The filters were taken in two pairs at slightly different times; the images were aligned on the planet.

## Colour assignment (A_chromatic: hues by wavelength (chromatic), F140M blue to F460M red)

| Filter | Hue |
|---|---|
| F140M | 240° |
| F210M | 160° |
| F300M | 80° |
| F460M | 0° |

The recorded light is infrared; all colours are an assignment, not "true" colours.

## Processing

calibrated stage-3 images (`_i2d.fits`) from MAST → row destriping on empty sky (no high-pass) + 2-D background (128 px) → aligned on the planet (WCS shifted by the target's mean positions, header MT_AVRA/MT_AVDEC) → close-up grid 0.031″/px centred on Neptune (`reproject_adaptive`; F300M/F460M upsampled ×2) → background from empty corners → asinh stretch (a = 0.01), white point from Neptune's disk (99.5 %), each filter normalised to its own white point → additive colour mixing → bad pixels filled with the local median, saturated cloud cores with the local maximum, white in all filters where saturated in any; no local adjustments. Notebook `12_neptune.ipynb`; all values in `params/neptune.json`.

## Credits

Data: NASA, ESA, CSA, STScI (programme 2739), retrieved via MAST. Processing: Tritium13.
