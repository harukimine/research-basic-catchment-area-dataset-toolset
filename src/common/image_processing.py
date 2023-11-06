import os
import numpy as np
from PIL import Image
from common.figure_setting import FigureSetting
from common.figure_setting import TiffTag
from common.util import save_json
from common.util import make_neighbor_xy
from common.setting import ValueSetting
from copy import deepcopy


class CommonImageProcessing:
    def __init__(self):
        self.image_tag = None
        self.save_dir = "catchment-area"
        self.geo_transform = None
        self.nodata = ValueSetting.nodata

    def set_save_dir(self, save_dir):
        self.save_dir = save_dir

    def set_tag(self, tag):
        self.image_tag = tag

    def get_x_resolution(self, tag):
        return tag[TiffTag.ModelPixelScaleTag][0]

    def get_y_resolution(self, tag):
        return tag[TiffTag.ModelPixelScaleTag][1]

    def get_x_origin(self, tag):
        return tag[TiffTag.ModelTiepointTag][3]

    def get_y_origin(self, tag):
        return tag[TiffTag.ModelTiepointTag][4]

    def change_resolution_to_km(self, resolution: tuple[float, float, float]) -> tuple[float, float, float]:
        crs_info = self.image_tag[TiffTag.GeoAsciiParamsTag][0]
        if "JGD_2011" in crs_info or "JGD2011" in crs_info:
            pass

    def set_coordinate_info(self, geo_transform: tuple[float, float, float, float, float, float]):
        self.geo_transform = geo_transform

    def is_out_of_array(self, array_size: tuple[int, int], x: int, y: int) -> bool:
        if (0 <= y < array_size[0]) and (0 <= x < array_size[1]):
            return False
        else:
            return True


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
        if image.mode in ["1", "L", "P", "I"]:
            setting = FigureSetting.integer_tiff
        else:
            setting = FigureSetting.tiff
        print("save", file_name, image.mode)
        path = os.path.join(self.save_dir, file_name + ".tif")
        image.save(path, **kwargs, **setting, tiffinfo=image.tag)

    def save_mono_tiff(self, image: Image.Image, file_name: str, **kwargs):
        image = self.convert_image_mono(image)
        self.save_tiff(image, file_name, **kwargs)

    def save_png(self, image: Image.Image, file_name: str, **kwargs):
        os.makedirs(self.save_dir, exist_ok=True)
        if image is None:
            return
        if image.mode in ["1", "L", "P", "I"]:
            setting = FigureSetting.integer_png
        else:
            setting = FigureSetting.png
        path = os.path.join(self.save_dir, file_name + ".png")
        image.save(path, **kwargs, **setting, tiffinfo=image.tag)

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
                if image.getpixel((x, y)) == self.nodata:
                    new_image.putpixel((x, y), 0)
                else:
                    new_image.putpixel((x, y), 1)
        return new_image

    def crop_image(self, image: Image.Image, bound_box: tuple[int, int, int, int]) -> Image.Image:
        """
        bound_box: (left, upper, right, lower)
        """
        new_image = image.crop(bound_box)
        new_image.tag = self._update_tag(image.tag, bound_box)
        return new_image

    def _update_tag(self, tag: dict, bound_box: tuple[int, int, int, int]) -> dict:
        new_tag = deepcopy(tag)
        dx = bound_box[0] * new_tag[TiffTag.ModelPixelScaleTag][0]
        dy = bound_box[1] * new_tag[TiffTag.ModelPixelScaleTag][1]
        width = bound_box[2] - bound_box[0]
        height = bound_box[3] - bound_box[1]
        new_tag[TiffTag.ImageWidth] = (width,)
        new_tag[TiffTag.ImageLength] = (height,)
        new_tag[TiffTag.ModelTiepointTag] = (
            new_tag[TiffTag.ModelTiepointTag][0],
            new_tag[TiffTag.ModelTiepointTag][1],
            new_tag[TiffTag.ModelTiepointTag][2],
            new_tag[TiffTag.ModelTiepointTag][3] + dx,
            new_tag[TiffTag.ModelTiepointTag][4] - dy,
            new_tag[TiffTag.ModelTiepointTag][5],
        )
        new_tag[TiffTag.RowsPerStrip] = (height,)
        new_tag[TiffTag.StripByteCounts] = (width * height,)
        return new_tag

    def crop_optimized_image(self, image: bytes) -> bytes:
        bound_box = self.get_bound_box_from_image(image)
        return self.crop_image(image, bound_box)

    def get_bound_box_from_image(self, image: bytes) -> tuple[int, int, int, int]:
        """left, upper, right, lower according to PIL.Image.crop"""
        image_array = np.array(image)
        lower = 0
        right = 0
        upper = image_array.shape[0] - 1
        left = image_array.shape[1] - 1
        for y, x in np.ndindex(image_array.shape):
            if image_array[y][x] == self.nodata:
                continue
            if upper > y:
                upper = y
            if lower < y:
                lower = y
            if left > x:
                left = x
            if right < x:
                right = x
        right = min(image_array.shape[1], right + 1)
        lower = min(image_array.shape[0], lower + 1)
        return (left, upper, right, lower)


class GeoJsonProcessing(CommonImageProcessing):
    def __init__(self):
        super().__init__()
        self.saved_tiff = None

    def save_tiff_as_geojson(self, tiff: bytes, file_name: str):
        self.set_saved_tiff(tiff)
        geojson = self.get_geojson_template()
        geojson["crs"]["properties"]["name"] = self.get_crs_from_tiff()
        geojson["features"][0]["geometry"] = self.get_coordinates_geometry_from_tiff()
        path = os.path.join(self.save_dir, file_name + ".geojson")
        save_json(geojson, path)

    def set_saved_tiff(self, tiff: bytes):
        self.saved_tiff = tiff

    def get_geojson_template(self):
        return {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
            },
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "watershed": "template",
                    },
                    "geometry": {"type": "Polygon", "coordinates": [[None]]},
                }
            ],
        }

    def get_crs_from_tiff(self) -> str:
        crs_info = self.saved_tiff.tag[TiffTag.GeoAsciiParamsTag][0]
        if crs_info is None:
            return None
        elif "JGD_2011" in crs_info or "JGD2011" in crs_info:
            return "urn:ogc:def:crs:EPSG::6668"
        elif "JGD_2000" in crs_info or "JGD2000" in crs_info:
            return "urn:ogc:def:crs:EPSG::4612"
        elif "WGS_1984" in crs_info or "WGS1984" in crs_info:
            return "urn:ogc:def:crs:EPSG::4326"
        elif "Tokyo Datum" in crs_info:
            return "urn:ogc:def:crs:EPSG::4301"
        else:
            return None

    def get_coordinates_geometry_from_tiff(self) -> dict[str, any]:
        array = np.array(self.saved_tiff)
        geometry = {"type": "Polygon", "coordinates": [[None]]}
        coordinates = []
        sx, sy = self.search_start_point(array)
        coordinates.append(self.get_coordinates(sx, sy))
        coordinates += self.get_continuous_coordinates(sx, sy)
        geometry["coordinates"] = [coordinates]
        return geometry

    def search_start_point(self, array: np.array) -> tuple[int, int]:
        for y, x in np.ndindex(array.shape):
            if array[y][x] == self.nodata:
                continue
            return (x, y)

    def get_continuous_coordinates(self, sx: int, sy: int) -> list[tuple[int, int]]:
        coordinates = []
        x = sx + 0
        y = sy + 0
        array = np.array(self.saved_tiff)
        searched_array = np.zeros(array.shape)
        while True:
            nx, ny = self.get_neighbor_xy_pixel(array, searched_array, x, y)
            if nx is None or ny is None:
                break
            coordinates.append(self.get_coordinates(nx, ny))
            searched_array[ny][nx] = 1
            x, y = nx, ny
        return coordinates

    def get_neighbor_xy_pixel(self, array: np.array, searched_array: np.array, x: int, y: int) -> tuple[int, int]:
        """Closest distance and few neighboring pixels"""
        neighbor_pixel_cnt_min = 9
        dist_min = 2
        candidate = (None, None)
        for nx, ny in make_neighbor_xy(x, y):
            if self.is_out_of_array(array.shape, nx, ny):
                continue
            if array[ny][nx] == self.nodata:
                continue
            if searched_array[ny][nx] == 1:
                continue
            dist = (x - nx) ** 2 + (y - ny) ** 2
            if dist_min >= dist:
                dist_min = dist
            else:
                continue
            neighbor_pixel_cnt = self.get_neighbor_pixel_cnt(array, nx, ny)
            if neighbor_pixel_cnt_min >= neighbor_pixel_cnt:
                neighbor_pixel_cnt_min = neighbor_pixel_cnt
                candidate = (nx, ny)
        return candidate

    def get_neighbor_pixel_cnt(self, array: np.array, x: int, y: int) -> int:
        cnt = 0
        for nx, ny in make_neighbor_xy(x, y):
            if self.is_out_of_array(array.shape, nx, ny):
                continue
            if array[ny][nx] == self.nodata:
                continue
            cnt += 1
        return cnt

    def get_coordinates(self, x: int, y: int) -> list[float, float]:
        originX = self.saved_tiff.tag[TiffTag.ModelTiepointTag][3]
        originY = self.saved_tiff.tag[TiffTag.ModelTiepointTag][4]
        dx = x * self.saved_tiff.tag[TiffTag.ModelPixelScaleTag][0]
        dy = y * self.saved_tiff.tag[TiffTag.ModelPixelScaleTag][1]
        return [originX + dx, originY - dy]


class ImageProcessing(PILProcessing, GeoJsonProcessing):
    def __init__(self):
        PILProcessing.__init__(self)
        self.used_image_module = "PIL"

    def set_used_image_module(self, module_name: str):
        if module_name not in ["PIL", "gdal"]:
            raise ValueError("module_name must be 'PIL' or 'gdal'.")
        self.used_image_module = module_name
