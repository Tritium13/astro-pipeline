# Ring Nebula (NGC 6720, M57) – JWST NIRCam + MIRI (W2_ionisation)

Planetary nebula in the constellation Lyra, observed with NIRCam and MIRI on the James Webb Space Telescope (Cycle 1 GO programme 1558, PI M. Barlow). Field of view ≈ 1.4 × 1.1 arcmin, north up, east left.

**Aesthetic version.** 50 % of the brightness is taken from NIRCam F335M (LRGB technique) to keep fine structure sharp. Colour and sharpness therefore come from data of different resolution: the fine detail is from NIRCam, while the MIRI colours are intrinsically blurrier (FWHM up to ≈0.49″ for F1500W). A resolution-matched reference version (W2s) shows the same colour distribution without this shortcut.

## Colour assignment (chosen freely, grouped by ionisation state, not by wavelength)

| Filter | Colour | Mainly traces |
|---|---|---|
| F1500W | blue | MIRI – [Ne III] (≈94 %), highly ionised gas |
| F162M | light blue | NIRCam – continuum, presumably free-free emission from ionised gas, plus hydrogen recombination lines |
| F212N | orange | NIRCam – molecular hydrogen (H2, ≈85 %) |
| F770W | red | MIRI – continuum, H2, [Ar II], PAH; concentric arcs most visible here |

Filter contents follow the estimates in Wesson et al. 2024 (MNRAS; arXiv:2308.09027, Table 1), which refer to part of the bright ring. Blue → red runs roughly from highly ionised gas near the hot central star to molecular gas further out. The recorded light is infrared; all colours are an assignment, not "true" colours.

## Processing

NIRCam: calibrated stage-3 images (`_i2d.fits`), row destriping with a local background model, common grid 0.063″/px (`reproject_adaptive`). MIRI: stage-3 mosaic (observation o001), reprojected onto the same grid, i.e. **upsampled from 0.111″/px** (this creates no new detail), then shifted by dy = +1.04, dx = -0.67 px (≈ 78 mas) to match NIRCam star positions (measured on F560W/F770W). Background from sky boxes (relative: the halo fills most of the field), asinh stretch per filter (each normalised to its own white point), additive colour mixing. Saturated star cores filled with white. No local adjustments. Parameters: `params/ngc6720_stretch.json`, `params/ngc6720_nircam_miri.json`. Code: `src/astropipe`.

## Credits

Data: NASA, ESA, CSA, STScI (programme 1558, PI M. Barlow), retrieved via MAST. Processing: Tritium13.
