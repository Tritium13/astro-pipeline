# Ring Nebula (NGC 6720, M57) – JWST NIRCam

Planetary nebula in the constellation Lyra, observed with the Near-Infrared Camera (NIRCam) of the James Webb Space Telescope (Cycle 1 GO programme 1558, PI M. Barlow). Field of view ≈ 1.6 × 1.2 arcmin, north up, east left.

## Colour assignment (C_physical: chosen freely, grouped by physical origin, not by wavelength)

| Filter | Colour | Mainly traces |
|---|---|---|
| F162M | blue | mainly continuum, presumably free-free emission from ionised gas, plus hydrogen recombination lines |
| F212N | orange-red | mainly molecular hydrogen (H2) |
| F300M | yellow | continuum, H2 and hydrogen lines (mixed) |
| F335M | gold | continuum and H2, plus the 3.3 µm PAH band (mixed) |

Filter contents follow the estimates in Wesson et al. 2024 (MNRAS; arXiv:2308.09027, Table 1), which refer to part of the bright ring. The recorded light is infrared; all colours are an assignment, not "true" colours.

## Processing

Calibrated stage-3 images (`_i2d.fits`) from MAST → row destriping of all four filters in 512-px column blocks using a local background model (16-px median cells; approximate correction of detector readout stripes – residual fine stripes and detector blocks remain) → common grid (0.063″/px, `reproject_adaptive`) → background subtraction from four sky boxes (the faint halo fills most of the field, so the background is relative) → asinh stretch per filter (each filter normalised to its own white point) → additive colour mixing. Saturated star cores filled with white. No local adjustments. Parameters: `params/ngc6720_stretch.json`, `params/ngc6720_color.json`. Code: `src/astropipe`.

## Credits

Data: NASA, ESA, CSA, STScI (programme 1558, PI M. Barlow), retrieved via MAST. Processing: Tritium13.
