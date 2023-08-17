import numpy as np
import sys
import logging

from flow_direction_rule import FlowDirectionRule
from common.image_processing import ImageProcessing
from common.setting import ValueSetting
from common.util import load_json
from common.util import make_neighbor_boundary_xy
from common.logging_decorator import logging_decorator
from pit_fill import PitFillAlgorithm


FLOW_DIRECTION_PATH = "base_data/FlowDir_30m_drone_mean.tif"
DAM_GEOJSON_PATH = "base_data/W01-14-g_Dam.geojson"
SAVE_DIR = "output/catchment-area"
sys.setrecursionlimit(20000)
logging.basicConfig(level=logging.INFO)


def main():
    dam_geojson = load_json(DAM_GEOJSON_PATH)
    catchment_area = CatchmentAreaArrangement()
    catchment_area.set_save_dir(SAVE_DIR)
    catchment_area.set_flow_direction_rule("D8")
    catchment_area.set_flow_direction(FLOW_DIRECTION_PATH)
    catchment_area.derive_flow_accumulation()
    catchment_area.set_dam_point_as_mouth(dam_geojson, "松尾", "小丸川")
    catchment_area.derive_catchment_area()
    catchment_area.derive_watershed()
    catchment_area.save_all_image_within_catchment_area()
    catchment_area.save_image()
    catchment_area.close_used_images()


class PitFill(ImageProcessing, FlowDirectionRule):
    def __init__(self):
        ImageProcessing.__init__(self)
        FlowDirectionRule.__init__(self)
        logging.info("init PitFill")
        self.dem = None
        self.pit_filled_dem = None
        self.altitude_correction = None
        self.pit_fill_rule = "normal"

    def set_elevation(self, path):
        self.dem = self.open_image(path)

    def set_pit_filled(self, path):
        self.pit_filled_dem = self.open_image(path)

    @logging_decorator
    def fill_pit(self):
        if self.dem is None:
            raise Exception("Elevation is not set.")
        elevation_array = np.array(self.dem)
        pit_filled_array = self.fill_pit_array(elevation_array)
        self.pit_filled_dem = self.open_image_from_array(pit_filled_array)
        altitude_correction = self.pit_filled_dem - self.dem
        self.altitude_correction = self.open_image_from_array(altitude_correction)

    def fill_pit_array(self, elevation_array: np.ndarray) -> np.ndarray:
        pit_filled_array = np.copy(elevation_array)
        if self.pit_fill_rule == "normal":
            pit_filled_array = PitFillAlgorithm.normal(pit_filled_array)
        elif self.pit_fill_rule == "Planchon_2001":
            pit_filled_array = PitFillAlgorithm.planchon_2001(pit_filled_array)
        elif self.pit_fill_rule == "yamazaki_2012":
            pit_filled_array = PitFillAlgorithm.yamazaki_2012(pit_filled_array)
        return pit_filled_array

    def save_image(self):
        self.save_tiff(self.dem, "dem")
        self.save_tiff(self.pit_filled_dem, "pit_filled_dem")
        self.save_tiff(self.altitude_correction, "altitude_correction")
        self.save_png(self.altitude_correction, "altitude_correction")

    def close_used_images(self):
        self.close_image(self.dem)
        self.close_image(self.pit_filled_dem)
        self.close_image(self.altitude_correction)


class FlowDirection(PitFill):
    def __init__(self):
        super().__init__()
        logging.info("init FlowDirection")
        self.flow_direction = None
        self.flow_direction_algorithm = "steepest_descent"

    def set_flow_direction(self, path: str):
        self.flow_direction = self.open_image(path)

    @logging_decorator
    def derive_flow_direction(self):
        if self.pit_filled_dem is None:
            self.fill_pit()
        flow_direction_array = self.get_flow_direction_array()
        self.flow_direction = self.open_image_from_array(flow_direction_array)

    def get_flow_direction_array(self) -> np.ndarray:
        array_size = self.get_array_size_from_image(self.pit_filled_dem)
        flow_direction_array = np.zeros(array_size, dtype=np.int8)
        pit_filled_array = np.array(self.dem)
        for y, x in np.ndindex(array_size):
            flow_direction_array[y][x] = self.get_flow_direction(
                array=pit_filled_array, x=x, y=y
            )
        return flow_direction_array

    def get_flow_direction(self, array, x, y) -> int:
        if self.flow_direction_algorithm == "steepest_descent":
            return self.get_steepest_descent_flow_direction(array, x, y)

    def get_steepest_descent_flow_direction(
        self, array: np.ndarray, x: int, y: int
    ) -> int:
        dx, dy = self.get_steepest_downstream_dx_dy(array, x, y)
        flow_direction = self.get_flow_direction_from_delta_xy(dx=dx, dy=dy)
        if flow_direction == 0:
            logging.info(f"No flow direction at ({x=}, {y=})")
        return flow_direction

    def get_steepest_downstream_dx_dy(
        self, array: np.ndarray, x: int, y: int
    ) -> tuple[int, int]:
        array_size = array.shape
        lowest_dem = array[y][x]
        downstream_dx = x.copy()
        downstream_dy = y.copy()
        for dx, dy in self.neighbor_delta_xy_generator():
            nx = x + dx
            ny = y + dy
            if self.is_out_of_array(array_size, nx, ny):
                continue
            neighbor_value = array[ny][nx]
            if lowest_dem < neighbor_value:
                lowest_dem = neighbor_value
                downstream_dx = dx
                downstream_dy = dy
        return downstream_dx, downstream_dy

    def save_image(self):
        super().save_image()
        self.save_tiff(self.flow_direction, "flow_direction")

    def close_used_images(self):
        super().close_used_images()
        self.close_image(self.flow_direction)


class FlowAccumulation(FlowDirection):
    def __init__(self):
        super().__init__()
        logging.info("init FlowAccumulation")
        self.flow_accumulation = None
        self.flow_accumulation_array = None

    def set_flow_accumulation(self, path):
        self.flow_accumulation = self.open_image(path)

    @logging_decorator
    def derive_flow_accumulation(self):
        if self.flow_direction is None:
            self.derive_flow_direction()
        flow_accumulation_array = self.get_flow_accumulation_array()
        self.flow_accumulation = self.open_image_from_array(flow_accumulation_array)

    def get_flow_accumulation_array(self) -> np.ndarray:
        flow_dir_array = np.array(self.flow_direction)
        flow_acc_array = self.calculate_flow_accumulation(flow_dir_array)

        return flow_acc_array

    def calculate_flow_accumulation(
        self,
        flow_direction_array: np.array,
    ) -> np.array:
        array_size = flow_direction_array.shape
        flow_accumulation_array = np.zeros(array_size, dtype=np.uint32)
        for y, x in np.ndindex(array_size):
            searched_array = np.zeros(array_size, dtype=np.bool_)
            while True:
                flow_direction = flow_direction_array[y][x]
                dx, dy = self.get_downstream_delta_xy(flow_direction)
                nx, ny = x + dx, y + dy
                if self.meet_break_condition(searched_array, nx, ny):
                    break
                searched_array[y][x] = True
                flow_accumulation_array[ny][nx] += 1
                x, y = nx, ny
        return flow_accumulation_array

    def meet_break_condition(self, searched_array, x, y):
        size = searched_array.shape
        return self.is_out_of_array(size, x, y) or searched_array[y][x]

    # c

    def save_image(self):
        super().save_image()
        self.save_tiff(self.flow_accumulation, "flow_accumulation")
        self.save_png(self.flow_accumulation, "flow_accumulation")

    def close_used_images(self):
        super().close_used_images()
        self.close_image(self.flow_accumulation)


class RiverMouth(FlowAccumulation):
    def __init__(self):
        super().__init__()
        logging.info("init RiverMouth")
        self.river_mouth = None
        self.river_mouth_threshold_km2 = 10

    def set_river_mouth_point(self, x, y):
        self.river_mouth = (x, y)

    def search_true_river_mouth(self, x: int, y: int) -> tuple[int, int]:
        if self.flow_accumulation is None:
            self.derive_flow_accumulation()
        flow_accumulation_array = np.array(self.flow_accumulation)
        if self.is_more_than_threshold(flow_accumulation_array[y][x]):
            return (x, y)
        return self._search_true_river_mouth(x, y)

    def is_more_than_threshold(self, flow_accumulation: int) -> bool:
        return flow_accumulation >= self.river_mouth_threshold_km2

    def _search_true_river_mouth(self, x: int, y: int):
        radius = 1
        flow_accumulation = np.array(self.flow_accumulation)
        while True:
            for nx, ny in make_neighbor_boundary_xy(x, y, radius):
                if self.is_more_than_threshold(flow_accumulation[y][x]):
                    logging.info(f"true river mouth is {radius} away")
                    return (nx, ny)
            radius += 1

    def derive_max_flowacc_as_river_mouth(self):
        if self.flow_accumulation is None:
            self.derive_flow_accumulation()
        self.river_mouth = self.get_max_flowacc_point()

    def get_max_flowacc_point(self) -> tuple:
        array = np.array(self.flow_accumulation)
        max_value = 0
        max_point = None
        for y, x in np.ndindex(array.shape):
            value = array[y][x]
            if max_value < value:
                max_value = value
                max_point = (x, y)
        return max_point

    def set_dam_point_as_mouth(self, geojson: dict[str, any], dam: str, river: str):
        coordinate = self.get_dam_coordinate_from_geojson(geojson, dam, river)
        x_origin = self.get_x_origin(self.image_tag)
        y_origin = self.get_y_origin(self.image_tag)
        x_resolution = self.get_x_resolution(self.image_tag)
        y_resolution = self.get_y_resolution(self.image_tag)
        x = int((coordinate[0] - x_origin) / x_resolution)
        y = int(-(coordinate[1] - y_origin) / y_resolution)
        self.set_river_mouth_point(x, y)
        if self.flow_accumulation:
            print(f"{self.flow_accumulation.getpixel((x, y))=}")

    def get_dam_coordinate_from_geojson(
        self, geojson: dict[str, any], dam: str, river
    ) -> list[float, float]:
        features = geojson["features"]
        for feature in features:
            dam_name = feature["properties"]["W01_001"]
            river_name = feature["properties"]["W01_003"]
            if dam_name == dam and river_name == river:
                return feature["geometry"]["coordinates"]
        raise ValueError(f"{dam} Dam in {river} not found in geojson")


class catchment_area(RiverMouth):
    def __init__(self):
        super().__init__()
        logging.info("init catchment_area")
        self.catchment_area_array: np.array = None
        self.catchment_area = None

    @logging_decorator
    def derive_catchment_area(self):
        if self.catchment_area_array is None:
            self.arrange_catchment_area_array()
        print(len(self.catchment_area_array[self.catchment_area_array > 0]))
        self.catchment_area = self.open_image_from_array(self.catchment_area_array)
        tmp = self.catchment_area_array
        flow_acc = np.array(self.flow_accumulation)
        flow_acc[tmp == 0] = 0
        flow_acc[flow_acc > 0] = 1
        flow_dir = np.array(self.flow_direction)
        array_size = flow_dir.shape
        tmp_iamge = self.open_image_from_array(flow_acc)
        self.save_mono_png(tmp_iamge, "tmp")

    def arrange_catchment_area_array(self):
        if self.flow_direction is None:
            self.derive_flow_direction()
        array_size = self.get_array_size_from_image(self.flow_direction)
        self.catchment_area_array = np.full(
            array_size, ValueSetting.nodata, dtype=np.int8
        )
        x = self.river_mouth[0]
        y = self.river_mouth[1]
        self.catchment_area_array[y][x] = 1
        flow_direction_array = np.array(self.flow_direction)
        self.identify_catchment_area_array_recursively(
            flow_direction_array=flow_direction_array, x=x, y=y
        )

    def identify_catchment_area_array_recursively(self, flow_direction_array, x, y):
        array_size = flow_direction_array.shape
        while True:
            self.catchment_area_array[y][x] = 1
            is_upend_stream = True
            num_neighbor_upstream = 0
            upstream_candidate_list: list[tuple[int, int]] = []
            for dx, dy in self.neighbor_delta_xy_generator():
                nx = x + dx
                ny = y + dy
                if self.is_out_of_array(array_size=array_size, x=nx, y=ny):
                    continue
                neighbor_flow_direction = flow_direction_array[ny][nx]
                if self.is_upstream(
                    neighbor_flow_direction=neighbor_flow_direction,
                    dx=dx,
                    dy=dy,
                ):
                    is_upend_stream = False
                    if self.is_already_searched(x=nx, y=ny):
                        continue
                    num_neighbor_upstream += 1
                    upstream_candidate_list.append((nx, ny))
            if is_upend_stream:
                break
            if num_neighbor_upstream == 0:
                break
            elif num_neighbor_upstream == 1:
                x, y = upstream_candidate_list[0]
            elif num_neighbor_upstream > 1:
                for nx, ny in upstream_candidate_list:
                    self.identify_catchment_area_array_recursively(
                        flow_direction_array=flow_direction_array, x=nx, y=ny
                    )

    def is_already_searched(self, x, y) -> bool:
        return self.catchment_area_array[y][x] != ValueSetting.nodata

    def save_image(self):
        super().save_image()
        self.save_tiff(self.catchment_area, "catchment_area")
        self.save_mono_png(self.catchment_area, "catchment_area")

    def close_used_images(self):
        super().close_used_images()
        self.close_image(self.catchment_area)


class Watershed(catchment_area):
    def __init__(self):
        super().__init__()
        logging.info("init Watershed")
        self.watershed = None

    def set_watershed(self, path):
        self.watershed = self.open_image(path)

    @logging_decorator
    def derive_watershed(self):
        logging.info("derive watershed")
        if self.catchment_area_array is None:
            self.arrange_catchment_area_array()
        watershed_array = self.get_watershed_array()
        self.watershed = self.open_image_from_array(watershed_array)
        print(len(watershed_array[watershed_array > 0]))

    def get_watershed_array(self) -> np.ndarray:
        watershed_array = self.catchment_area_array.copy()
        for y, x in np.ndindex(watershed_array.shape):
            if watershed_array[y][x] == ValueSetting.nodata:
                continue
            if self.is_not_watershed(self.catchment_area_array, x=x, y=y):
                watershed_array[y][x] = ValueSetting.nodata
        return watershed_array

    def is_not_watershed(self, watershed_array, x, y):
        watershed_pixel_cnt = 0
        array_size = watershed_array.shape
        for dx, dy in self.neighbor_delta_xy_generator(include_center=True):
            if dx * dy != 0:
                continue
            nx = x + dx
            ny = y + dy
            if self.is_out_of_array(array_size=array_size, x=nx, y=ny):
                continue
            if watershed_array[ny][nx] == 1:
                watershed_pixel_cnt += 1
        if watershed_pixel_cnt >= 5:
            return True
        else:
            return False

    def save_image(self):
        super().save_image()
        self.save_tiff(self.watershed, "watershed")
        self.save_mono_png(self.watershed, "watershed")

    def close_used_images(self):
        super().close_used_images()
        self.close_image(self.watershed)


class CatchmentAreaArrangement(Watershed):
    def __init__(self):
        super().__init__()
        logging.info("init CatchmentAreaArrangement")

    def clip_by_catchment_area(self, image: bytes) -> bytes:
        if self.catchment_area_array is None:
            self.arrange_catchment_area_array()
        image_array = np.array(image)
        for y, x in np.ndindex(image_array.shape):
            if self.catchment_area_array[y][x] == ValueSetting.nodata:
                image_array[y][x] = ValueSetting.nodata
        return self.open_image_from_array(image_array)

    def save_all_image_within_catchment_area(self):
        bound_box = self.get_bound_box_from_image(self.catchment_area)
        save_dict = {
            "catchment_area": self.catchment_area,
            "dem": self.dem,
            "pit_filled_dem": self.pit_filled_dem,
            "altitude_correction": self.altitude_correction,
            "flow_direction": self.flow_direction,
            "flow_accumulation": self.flow_accumulation,
            "watershed": self.watershed,
        }
        for file_name, image in save_dict.items():
            if image is None:
                continue
            image = self.clip_by_catchment_area(image)
            image = self.crop_image(image, bound_box)
            file_name = "clipped_" + file_name
            if file_name == "clipped_watershed":
                self.save_tiff_as_geojson(image, file_name)
            if file_name in ["clipped_catchment_area", "clipped_watershed"]:
                self.save_mono_png(image, file_name)
            else:
                self.save_tiff(image, file_name)
            self.close_image(image)


if __name__ == "__main__":
    main()
