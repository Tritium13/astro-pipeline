"""astropipe – reproducible colour images from public JWST imaging data.

Modules follow the stages of the notebooks:
    bands         filter names, wavelengths, sorting
    mast          stage 1: query and download i2d products
    clean         optional: destriping of i2d images before stage 3
    registration  stage 3: common grid, reprojection, star check
    stretch       stage 4: saturated holes, sky boxes, background, asinh stretch
    color         stage 5: hues and additive colour mixing
    export        stage 6: crop, orientation, file export
"""
__version__ = "0.1.0"
