import math
import numpy as np
import sys
from PIL import Image

from flow_direction_rule import FlowDirectionRule
from common.image_processing import ImageProcessing
from pit_fill import PitFillAlgorithm


FLOW_DIRECTION_PATH = "base_file/FlowDir_30m_drone_mean.tif"
RIVER_MOUTH_POINT = (856, 752)
SAVE_DIR = "base_file/catchment-area"
sys.setrecursionlimit(20000)


def main():
    catchment_area = CatchmentAreaArrangement()
    catchment_area.set_save_dir(SAVE_DIR)
    catchment_area.set_flow_direction_rule("D8")
    catchment_area.set_flow_direction(FLOW_DIRECTION_PATH)
    catchment_area.set_river_mouth_point(*RIVER_MOUTH_POINT)
    catchment_area.derive_catchment_area()
    catchment_area.derive_watershed()
    catchment_area.save_image()


class PitFill(ImageProcessing, FlowDirectionRule):
    def __init__(self):
        ImageProcessing.__init__()
        FlowDirectionRule.__init__()
        print("init PitFill")
        self.image_tag = None
        self.elevation = None
        self.pit_filled = None
        self.pit_fill_rule = "normal"

    def set_tag(self, tag):
        self.image_tag = tag

    def set_elevation(self, path):
        self.elevation = Image.open(path)
        self.set_tag(self.elevation.tag)

    def set_pit_filled(self, path):
        self.pit_filled = Image.open(path)
        self.set_tag(self.pit_filled.tag)

    def fill_pit(self):
        if self.elevation is None:
            raise Exception("Elevation is not set.")
        elevation_array = np.array(self.elevation)
        pit_filled_array = self.fill_pit_array(elevation_array)
        self.pit_filled = Image.fromarray(pit_filled_array)

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
        super().save_image()
        self.save_tiff(self.elevation, "elevation")
        self.save_tiff(self.pit_filled, "pit_filled")
        self.close_image(self.elevation)
        self.close_image(self.pit_filled)


class FlowDirection(PitFill):
    def __init__(self):
        super().__init__()
        print("init FlowDirection")
        self.flow_direction = None
        self.flow_direction_algorithm = "steepest_descent"

    def set_flow_direction(self, path):
        self.flow_direction = Image.open(path)
        self.set_tag(self.flow_direction.tag)

    def derive_flow_direction(self):
        if self.pit_filled is None:
            self.fill_pit()
        flow_direction_array = self.get_flow_direction_array()
        self.flow_direction = Image.fromarray(flow_direction_array)

    def get_flow_direction_array(self):
        array_size = self.get_array_size_from_Image(self.pit_filled)
        flow_direction_array = np.zeros(array_size, dtype=np.int8)
        pit_filled_array = np.array(self.elevation)
        for y, row in enumerate(flow_direction_array):
            for x, pixel in enumerate(row):
                flow_direction_array[y][x] = self.get_flow_direction(
                    array=pit_filled_array, x=x, y=y
                )
        return flow_direction_array

    def get_flow_direction(self, array, x, y):
        if self.flow_direction_algorithm == "steepest_descent":
            return self.get_steepest_descent_flow_direction(array, x, y)

    def get_steepest_descent_flow_direction(self, array, x, y):
        array_size = array.shape
        max_slope = 0
        down_stream_delta_x = 0
        down_stream_delta_y = 0
        center_value = array[y][x]
        for delta_y in self.delta_y_range:
            for delta_x in self.delta_x_range:
                nx = x + delta_x
                ny = y + delta_y
                if self.is_out_of_array(array_size, nx, ny):
                    continue
                neighbor_value = array[ny][nx]
                if center_value < neighbor_value:
                    continue
                dist = math.sqrt(delta_x**2 + delta_y**2)
                slope = (center_value - neighbor_value) / dist
                if max_slope < slope:
                    max_slope = slope
                    down_stream_delta_x = delta_x
                    down_stream_delta_y = delta_y
        flow_direction = self.get_flow_direction_from_delta_index(
            delta_x=down_stream_delta_x, delta_y=down_stream_delta_y
        )
        if flow_direction == 0:
            print(f"No flow direction at ({x=}, {y=})")
        return flow_direction

    def save_image(self):
        super().save_image()
        self.save_tiff(self.flow_direction, "flow_direction")
        self.close_image(self.flow_direction)


class FlowAccumulation(FlowDirection):
    def __init__(self):
        super().__init__()
        print("init FlowAccumulation")
        self.flow_accumulation = None

    def set_flow_accumulation(self, path):
        self.flow_accumulation = Image.open(path)
        self.set_tag(self.flow_accumulation.tag)

    def derive_flow_accumulation(self):
        if self.flow_direction is None:
            self.derive_flow_direction()
        flow_accumulation_array = self.get_flow_accumulation_array()
        self.flow_accumulation = Image.fromarray(flow_accumulation_array)

    def get_flow_accumulation_array(self):
        array_size = self.get_array_size_from_Image(self.flow_direction)
        flow_accumulation_array = np.zeros(array_size, dtype=np.uint32)
        flow_direction_array = np.array(self.flow_direction)
        for y, row in enumerate(flow_accumulation_array):
            for x, pixel in enumerate(row):
                flow_accumulation_array[y][x] = self.get_flow_accumulation(
                    array=flow_direction_array, x=x, y=y
                )
        return flow_accumulation_array

    def get_flow_accumulation(self, array, x, y):
        flow_direction = array[y][x]
        if flow_direction == 0:
            return 0
        delta_x, delta_y = self.get_downstream_delta_index(flow_direction)
        nx = x + delta_x
        ny = y + delta_y

        return self.flow_accumulation_array[ny][nx] + 1

    def save_image(self):
        super().save_image()
        self.save_tiff(self.flow_accumulation, "flow_accumulation")
        self.close_image(self.flow_accumulation)


class RiverMouth(FlowAccumulation):
    def __init__(self):
        super().__init__()
        print("init RiverMouth")
        self.river_mouth = None

    def set_river_mouth_point(self, x, y):
        self.river_mouth = (x, y)

    def derive_river_mouth(self):
        if self.flow_accumulation is None:
            self.derive_flow_accumulation()
        self.river_mouth = self.get_river_mouth_point()

    def get_river_mouth_point(self):
        array = np.array(self.flow_accumulation)
        max_value = 0
        max_point = None
        for y, row in enumerate(array):
            for x, value in enumerate(row):
                if max_value < value:
                    max_value = value
                    max_point = (x, y)
        return max_point


class catchment_area(RiverMouth):
    def __init__(self):
        super().__init__()
        print("init catchment_area")
        self.catchment_area_array = None
        self.catchment_area = None

    def derive_catchment_area(self):
        if self.catchment_area_array is None:
            self.arrange_catchment_area_array()
        self.catchment_area = Image.fromarray(self.catchment_area_array)

    def arrange_catchment_area_array(self):
        if self.flow_direction is None:
            self.derive_flow_direction()
        array_size = self.get_array_size_from_Image(self.flow_direction)
        self.catchment_area_array = np.zeros(array_size, dtype=np.int8)
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
            for delta_y in self.delta_y_range:
                for delta_x in self.delta_x_range:
                    nx = x + delta_x
                    ny = y + delta_y
                    if self.is_center(delta_x=delta_x, delta_y=delta_y):
                        continue
                    if self.is_out_of_array(array_size=array_size, x=nx, y=ny):
                        continue
                    neighbor_flow_direction = flow_direction_array[ny][nx]
                    if self.is_upstream(
                        neighbor_flow_direction=neighbor_flow_direction,
                        delta_x=delta_x,
                        delta_y=delta_y,
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

    def is_already_searched(self, x, y):
        return self.catchment_area_array[y][x] != 0

    def save_image(self):
        super().save_image()
        self.save_mono_tiff(self.catchment_area, "catchment_area")
        self.save_mono_png(self.catchment_area, "catchment_area")
        self.close_image(self.catchment_area)


class Watershed(catchment_area):
    def __init__(self):
        super().__init__()
        print("init Watershed")
        self.watershed = None

    def set_watershed(self, path):
        self.watershed = Image.open(path)
        self.set_tag(self.watershed.tag)

    def derive_watershed(self):
        if self.catchment_area_array is None:
            self.arrange_catchment_area_array()
        watershed_array = self.get_watershed_array()
        self.watershed = Image.fromarray(watershed_array)

    def get_watershed_array(self):
        watershed_array = self.catchment_area_array.copy()
        for y, row in enumerate(watershed_array):
            for x, pixel in enumerate(row):
                if pixel == 0:
                    continue
                if self.is_in_watershed(self.catchment_area_array, x=x, y=y):
                    watershed_array[y][x] = 0
        return watershed_array

    def is_in_watershed(self, watershed_array, x, y):
        watershed_pixel_cnt = 0
        array_size = watershed_array.shape
        for delta_y in self.delta_y_range:
            for delta_x in self.delta_x_range:
                nx = x + delta_x
                ny = y + delta_y
                if self.is_out_of_array(array_size=array_size, x=nx, y=ny):
                    continue
                if watershed_array[ny][nx] == 1:
                    watershed_pixel_cnt += 1

        if watershed_pixel_cnt == 9:
            return True
        else:
            return False

    def save_image(self):
        super().save_image()
        self.save_mono_tiff(self.watershed, "watershed")
        self.save_mono_png(self.watershed, "watershed")
        self.close_image(self.watershed)


class CatchmentAreaArrangement(Watershed):
    def __init__(self):
        super().__init__()
        print("init CatchmentAreaArrangement")

    def clip_by_watershed(self):
        pass

    def save_image(self):
        super().save_image()


if __name__ == "__main__":
    main()
