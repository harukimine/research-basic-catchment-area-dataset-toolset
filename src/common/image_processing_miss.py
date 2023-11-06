import os
from PIL import Image
from common.figure_setting import FigureSetting
from osgeo import gdal


class CommonImageProcessing:
    def __init__(self):
        self.image_tag = None
        self.save_dir = "catchment-area"
        self.geo_transform = None

    def set_save_dir(self, save_dir):
        self.save_dir = save_dir

    def set_tag(self, tag):
        self.image_tag = tag

    def set_coordinate_info(self, geo_transform: tuple[float, float, float, float, float, float]):
        self.geo_transform = geo_transform


class PILProcessing(CommonImageProcessing):
    def __init__(self):
        super().__init__()

    def open_image(self, file_path: str) -> Image.Image:
        image = Image.open(file_path)
        self.set_tag(image.tag)
        return image

    def open_image_from_array(self, array: list[list[int]]) -> Image.Image:
        image = Image.fromarray(array)
        image.tag = self.image_tag
        return image

    def get_array_shape_from_image(self, image: Image) -> tuple[int, int]:
        return image.height, image.width

    def save_tiff(self, image: Image.Image, file_name: str, **kwargs):
        os.makedirs(self.save_dir, exist_ok=True)
        if image is None:
            return
        if image.mode in ["1", "L"]:
            setting = FigureSetting.monochrome_tiff
        else:
            setting = FigureSetting.tiff
        path = os.path.join(self.save_dir, file_name + ".tif")
        image.save(path, **kwargs, **setting, tiffinfo=self.image_tag)

    def save_mono_tiff(self, image: Image.Image, file_name: str, **kwargs):
        image = self.convert_image_mono(image)
        self.save_tiff(image, file_name, **kwargs)

    def save_png(self, image: Image.Image, file_name: str, **kwargs):
        os.makedirs(self.save_dir, exist_ok=True)
        if image.mode in ["1", "L"]:
            setting = FigureSetting.monochrome_png
        else:
            setting = FigureSetting.png
        path = os.path.join(self.save_dir, file_name + ".png")
        image.save(path, **kwargs, **setting, tiffinfo=self.image_tag)

    def save_mono_png(self, image: Image.Image, file_name: str, **kwargs):
        image = self.convert_image_mono(image)
        self.save_png(image, file_name, **kwargs)

    def close_image(self, image: Image.Image):
        if image is not None:
            image.close()

    def convert_image_mono(self, image: Image.Image) -> Image.Image:
        new_image = Image.new(mode="1", size=image.size)
        new_image.tag = image.tag
        for y in range(image.height):
            for x in range(image.width):
                if image.getpixel((x, y)) == 0:
                    new_image.putpixel((x, y), 0)
                else:
                    new_image.putpixel((x, y), 1)
        return new_image

    def crop_image(self, image: Image.Image, bound_box: tuple[int, int, int, int]) -> Image.Image:
        new_image = image.crop(*bound_box)
        new_tag = image.tag.copy()
        dx = bound_box[0] * new_tag["XResolution"] / new_tag["ResolutionUnit"]
        dy = bound_box[1] * new_tag["YResolution"] / new_tag["ResolutionUnit"]
        new_tag["XPosition"] = str(float(new_tag["XPosition"]) + dx)
        new_tag["YPosition"] = str(float(new_tag["YPosition"]) + dy)
        new_tag["ImageWidth"] = str(bound_box[2] - bound_box[0])
        new_tag["ImageLength"] = str(bound_box[3] - bound_box[1])
        new_image.tag = new_tag
        return new_image


class GdalProcessing(CommonImageProcessing):
    def __init__(self):
        super().__init__()

    def open_image(self, file_path: str) -> gdal:
        image: gdal.Dataset = gdal.Open(file_path)
        self.set_tag(image.GetMetadata())
        self.set_coordinate_info(image.GetGeoTransform())

    def open_image_from_array(self, array: list[list[int]]) -> gdal:
        image: gdal.Dataset = gdal.Open(array)
        return image.SetGeoTransform(self.geo_transform)

    def get_array_shape_from_image(self, image: gdal.Dataset) -> tuple[int, int]:
        return image.RasterYSize, image.RasterXSize

    def save_tiff(self, image: gdal.Dataset, file_name: str, **kwargs):
        os.makedirs(self.save_dir, exist_ok=True)
        if image is None:
            return
        path = os.path.join(self.save_dir, file_name + ".tif")
        driver: gdal.Driver = gdal.GetDriverByName("GTiff")
        driver.CreateCopy(path, image, **kwargs)

    def save_mono_tiff(self, image: gdal.Dataset, file_name: str, **kwargs):
        image = self.convert_image_mono(image)
        self.save_tiff(image, file_name, **kwargs)

    def save_png(self, image: gdal.Dataset, file_name: str, **kwargs):
        os.makedirs(self.save_dir, exist_ok=True)
        if image is None:
            return
        path = os.path.join(self.save_dir, file_name + ".png")
        driver: gdal.Driver = gdal.GetDriverByName("PNG")
        driver.CreateCopy(path, image, **kwargs)

    def save_mono_png(self, image: gdal.Dataset, file_name: str, **kwargs):
        mono_image = self.convert_image_mono(image)
        self.save_png(mono_image, file_name, **kwargs)

    def close_image(self, image: gdal.Dataset):
        if image is not None:
            image = None

    def convert_image_mono(self, image: gdal.Dataset) -> gdal:
        new_image: gdal.Driver = gdal.GetDriverByName("MEM").CreateCopy("", image)
        new_image = new_image.ReadAsArray()
        new_image[new_image == 0] = 0
        new_image[new_image != 0] = 1
        return new_image

    def crop_image(self, image: gdal.Dataset, bound_box: tuple[int, int, int, int]) -> gdal:
        """
        bound_box = (left, upper, right, lower)
        GetGeoTransform():
        (originX, Width, rotation angle, originY, rotation angle, Height)
        """
        gt = self.geo_transform.copy()
        x = bound_box[0]
        y = bound_box[1]
        width = bound_box[2] - bound_box[0]
        height = bound_box[3] - bound_box[1]
        cropped_image: gdal.Dataset = image.ReadAsArray(x, y, width, height)
        gt[0] += x * gt[1]
        gt[3] += y * gt[5]
        cropped_image.SetGeoTransform(gt)
        return cropped_image


class ImageProcessing(PILProcessing, GdalProcessing):
    def __init__(self):
        PILProcessing.__init__()
        GdalProcessing.__init__()
        self.used_image_module = "PIL"

    def set_used_image_module(self, module_name: str):
        if module_name not in ["PIL", "gdal"]:
            raise ValueError("module_name must be 'PIL' or 'gdal'.")
        self.used_image_module = module_name

    def open_image(self, file_path: str):
        if self.used_image_module == "PIL":
            return PILProcessing.open_image(file_path)
        elif self.used_image_module == "gdal":
            return GdalProcessing.open_image(file_path)

    def open_image_from_array(self, array: list[list[int]]) -> any:
        if self.used_image_module == "PIL":
            return PILProcessing.open_image_from_array(array)
        elif self.used_image_module == "gdal":
            return GdalProcessing.open_image_from_array(array)

    def get_array_shape_from_image(self, image: bytes) -> tuple[int, int]:
        if self.used_image_module == "PIL":
            return PILProcessing.get_array_shape_from_image(image)
        elif self.used_image_module == "gdal":
            return GdalProcessing.get_array_shape_from_image(image)

    def save_tiff(self, image: bytes, file_name: str, **kwargs):
        if self.used_image_module == "PIL":
            PILProcessing.save_tiff(image, file_name, **kwargs)
        elif self.used_image_module == "gdal":
            GdalProcessing.save_tiff(image, file_name, **kwargs)

    def save_mono_tiff(self, image: bytes, file_name: str, **kwargs):
        if self.used_image_module == "PIL":
            PILProcessing.save_mono_tiff(image, file_name, **kwargs)
        elif self.used_image_module == "gdal":
            GdalProcessing.save_mono_tiff(image, file_name, **kwargs)

    def save_png(self, image: bytes, file_name: str, **kwargs):
        if self.used_image_module == "PIL":
            PILProcessing.save_png(image, file_name, **kwargs)
        elif self.used_image_module == "gdal":
            GdalProcessing.save_png(image, file_name, **kwargs)

    def save_mono_png(self, image: bytes, file_name: str, **kwargs):
        if self.used_image_module == "PIL":
            PILProcessing.save_mono_png(image, file_name, **kwargs)
        elif self.used_image_module == "gdal":
            GdalProcessing.save_mono_png(image, file_name, **kwargs)

    def close_image(self, image: bytes):
        if self.used_image_module == "PIL":
            PILProcessing.close_image(image)
        elif self.used_image_module == "gdal":
            GdalProcessing.close_image(image)

    def convert_image_mono(self, image: bytes) -> any:
        if self.used_image_module == "PIL":
            return PILProcessing.convert_image_mono(image)
        elif self.used_image_module == "gdal":
            return GdalProcessing.convert_image_mono(image)

    def crop_image(self, image: bytes, bound_box: tuple[int, int, int, int]) -> any:
        if self.used_image_module == "PIL":
            return PILProcessing.crop_image(image, bound_box)
        elif self.used_image_module == "gdal":
            return GdalProcessing.crop_image(image, bound_box)
