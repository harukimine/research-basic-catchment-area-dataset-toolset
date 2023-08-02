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
    monochrome = {
        "bbox_inches": "tight",
        "pad_inches": 0,
    }
    monochrome_png = {
        **monochrome,
        "format": "png",
    }
    monochrome_tiff = {
        **monochrome,
        "format": "tiff",
    }
