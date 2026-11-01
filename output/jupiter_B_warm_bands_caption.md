# Jupiter – JWST NIRCam

Jupiter, observed on 2022-07-27 with NIRCam on the James Webb Space Telescope (programme 1373, observation o008). Field of view ≈ 50″ × 50″, north up, east left. Only two filters, exposed at the same time; a third colour channel is synthetic.

## Colour assignment (B_warm_bands: chosen freely: F212N gold-orange, F335M cyan-blue)

| Filter | Hue |
|---|---|
| F212N | 35° |
| F335M | 200° |

The recorded light is infrared; all colours are an assignment, not "true" colours.

## Processing

calibrated stage-3 images (`_i2d.fits`) from MAST, one pair of filters exposed simultaneously (no rotation between them) → row destriping on empty sky (no high-pass) → close-up grid 0.031″/px centred on Jupiter (`reproject_adaptive`; F335M upsampled ×2) → background from empty corners → asinh stretch (a = 0.2), white point from the measured disk pixels (99.5 %), each filter normalised to its own white point → additive colour mixing → bad/flagged pixels filled with the local median; large saturated areas on the planet (bright limb haze, around the Great Red Spot in F335M) set to white; no local adjustments. Notebook `14_jupiter.ipynb`; all values in `params/jupiter.json`.

## Credits

Data: NASA, ESA, CSA, STScI (programme 1373), retrieved via MAST. Processing: Tritium13.
