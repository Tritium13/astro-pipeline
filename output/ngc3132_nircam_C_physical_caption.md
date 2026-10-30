# Southern Ring Nebula (NGC 3132) – JWST NIRCam

Planetary nebula in the constellation Vela, observed on 3 June 2022 with the Near-Infrared Camera (NIRCam) of the James Webb Space Telescope as part of the Early Release Observations (programme 2733). Field of view ≈ 1.7 × 1.7 arcmin, north up, east left.

## Colour assignment (chosen freely, grouped by physical origin, not by wavelength)

| Filter | Colour | Mainly traces |
|---|---|---|
| F090W | yellow | broadband: stars, scattered light |
| F187N | light blue | ionised hydrogen (Paschen-α) |
| F212N | orange | molecular hydrogen (H2) |
| F356W | yellow-orange | broadband: stars, nebula |
| F405N | blue | ionised hydrogen (Brackett-α) |
| F470N | red | molecular hydrogen (H2) |

The recorded light is infrared; all colours are an assignment, not "true" colours.

## Processing

Calibrated stage-3 images (`_i2d.fits`) from MAST → common grid (0.063″/px, `reproject_adaptive`) → background subtraction from empty sky regions → asinh stretch per filter (each filter normalised to its own white point, so relative brightness between filters is not preserved) → additive colour mixing. Saturated star cores filled with white. No local adjustments. All parameters: `params/ngc3132_stretch.json`, `params/ngc3132_color.json`.

Known limitation: detector patterns (stripes, brightness steps) in F187N/F212N are suppressed by the black point, not removed.

## Credits

Data: NASA, ESA, CSA, STScI (JWST Early Release Observations, programme 2733), retrieved via MAST. Processing: Tritium13.
