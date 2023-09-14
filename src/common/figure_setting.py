class FigureSetting:
    default = {
        "dpi": 300,
        "bbox_inches": "tight",
        "pad_inches": 0,
    }
    png = {
        **default,
        "format": "png",
    }
    tiff = {
        **default,
        "format": "tiff",
    }
    gif = {
        **default,
        "format": "gif",
        "save_all": True,
    }
    integer = {
        "bbox_inches": "tight",
        "pad_inches": 0,
    }
    integer_png = {
        **integer,
        "format": "png",
    }
    integer_tiff = {
        **integer,
        "format": "tiff",
    }


class TiffTag:
    # used to reset coordinate
    ImageWidth = 256
    ImageLength = 257
    BitsPerSample = 258
    Compression = 259
    ModelTiepointTag = 33922
    GDAL_METADATA = 42112
    PhotometricInterpretation = 262
    GDAL_NODATA = 42113
    ModelPixelScaleTag = 33550
    StripOffsets = 273
    SampleFormat = 339
    SamplesPerPixel = 277
    RowsPerStrip = 278
    StripByteCounts = 279
    PlanarConfiguration = 284

    GeoKeyDirectoryTag = 34735
    GeoDoubleParamsTag = 34736
    GeoAsciiParamsTag = 34737
