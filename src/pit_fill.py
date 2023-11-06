import numpy as np


class NormalPitFill:
    """
    fill pit by adding correction to the lowest neighbor cell.
    to avoid infinite loop, the correction is added to the lowest neighbor cell.
    parameters: correction, const_for_skip_loop
    """

    def pit_fill(self, dem_array: np.ndarray) -> np.ndarray:
        y_size, x_size = dem_array.shape
        loop_cnt_size = 100
        loop_cnt = 0
        correction = 0.01
        while True:
            depression = 0
            loop_cnt += 1
            if loop_cnt > loop_cnt_size:
                break
            for y in range(1, y_size - 1):
                for x in range(1, x_size - 1):
                    dem = dem_array[y][x]
                    min_dem = self._search_lowest_neighbor_dem(dem_array, x, y)
                    if min_dem > dem:
                        dem_array[y][x] = min_dem + correction
                        depression += 1
            if depression == 0:
                break

    def _search_lowest_neighbor_dem(self, dem_array: np.ndarray, x: int, y: int) -> bool:
        y_size, x_size = dem_array.shape
        dem = dem_array[y][x]
        min_dem = float("inf")
        const_for_skip_loop = 0.1
        for ny in range(max(y - 1, 0), min(y + 2, y_size)):
            for nx in range(max(x - 1, 0), min(x + 2, x_size)):
                neighbor_dem = dem_array[ny][nx]
                if min_dem > neighbor_dem:
                    min_dem = neighbor_dem
        if min_dem < dem:
            return min_dem
        else:
            return max(dem + const_for_skip_loop, min_dem)


class Planchon2001PitFill:
    """
    A fast, simple and versatile algorithm to fill the depressions of digital elevation models
    by O. Planchon and F. Darboux, Catena 46 (2001) 159-176
    it first inundates the surface with a thick layer of water and then removes the excess water.
    versatile: depressions can be replaced with a surface either strictly horizontal, or slightly sloping.
    """

    def pit_fill(self, dem_array: np.ndarray) -> np.ndarray:
        """this is the main method of this class and only called from outside"""
        self.initialize_common_variables(dem_array)
        self.initialize_surface_to_infinite_except_boundary()
        self.implement_improved_direct_filling_algorithm()

    def initialize_common_variables(self, dem_array: np.ndarray):
        self.initialize_depth_variable()
        self.set_eta()
        self.set_dem_array(dem_array)
        self.set_neighbor_rules()

    def initialize_depth_variable(self, MAX_DEPTH=2000):
        """ "
        MAX_DEPTH is a constant initialized to an acceptable value
        depending on the size of the program's stack
        """
        self.depth = 0
        self.MAX_DEPTH = MAX_DEPTH

    def set_eta(self, ETA=0.01):
        """
        ETA is a small positive value
        if ETA == 0, surface will be strictly horizontal
        if ETA > 0, surface will be sloping
        """
        if self.eta < 0:
            raise ValueError("ETA must be positive")
        self.eta = ETA

    def set_dem_array(self, dem_array: np.ndarray):
        self.dem_array = dem_array
        self.y_size, self.x_size = dem_array.shape

    def set_neighbor_rules(self):
        y_max = self.y_size - 1
        x_max = self.x_size - 1
        self.y0 = [0, y_max, 0, y_max, 0, y_max, 0, y_max]
        self.x0 = [0, x_max, x_max, 0, x_max, 0, 0, x_max]
        self.dy = [0, 0, 1, -1, 0, 0, 1, -1]
        self.dx = [1, -1, 0, 0, -1, 1, 0, 0]
        self.yf = [1, -1, -y_max, y_max, 1, -1, -y_max, y_max]
        self.xf = [-x_max, x_max, -1, 1, x_max, -x_max, 1, -1]

    def initialize_surface_to_infinite_except_boundary(self):
        self.surface = self.dem_array.copy()
        for y in range(self.y_size):
            for x in range(self.x_size):
                if not self._is_on_boundary(x=x, y=y):
                    self.surface[y][x] = float("inf")

    def next_to_cell(self, x: int, y: int, index: int) -> tuple:
        nx = x + self.dx[index]
        ny = y + self.dy[index]
        if self._is_outside_boundary(x=nx, y=ny):
            nx += self.xf[index]
            ny += self.yf[index]
            if self._is_outside_boundary(x=nx, y=ny):
                return False
        return True

    def existing_neighbor_generator(self, x: int, y: int) -> tuple[int, int]:
        for yn in range(y - 1, y + 2):
            for xn in range(x - 1, x + 2):
                if self._is_outside_boundary(x=xn, y=yn):
                    continue
                if xn == x and yn == y:
                    continue
                yield xn, yn

    def whole_range_generator(self) -> tuple[int, int]:
        for y in range(self.y_size):
            for x in range(self.x_size):
                yield x, y

    def _is_outside_boundary(self, x: int, y: int) -> bool:
        return y < 0 or y >= self.y_size or x < 0 or x >= self.x_size

    def _is_on_boundary(self, x: int, y: int) -> bool:
        return y == 0 or y == self.y_size - 1 or x == 0 or x == self.x_size - 1

    def implement_direct_filling_algorithm(self):
        while True:
            is_surface_modified = False
            for x, y in self.whole_range_generator():
                if self._is_on_boundary(x=x, y=y):
                    continue
                if self._not_need_to_modify_surface(x=x, y=y):
                    continue
                for nx, ny in self.existing_neighbor_generator(x=x, y=y):
                    if self.convergence_operation(x=x, y=y, nx=nx, ny=ny):
                        is_surface_modified = True
                        return self.implement_direct_filling_algorithm()
                    elif self.did_convergence2(x=x, y=y, nx=nx, ny=ny):
                        is_surface_modified = True
            if is_surface_modified is False:
                break

    def _not_need_to_modify_surface(self, x: int, y: int) -> bool:
        return self.surface[y][x] <= self.dem_array[y][x]

    def convergence_operation(self, x: int, y: int, nx: int, ny: int) -> bool:
        """determine value at a surface cell"""
        dem = self.dem_array[y][x]
        neighbor_surface = self.surface[ny][nx]
        if dem >= neighbor_surface + self.eta:
            self.surface[y][x] = dem
            return True
        return False

    def did_convergence2(self, x: int, y: int, nx: int, ny: int) -> bool:
        """set provisional value at a surface cell"""
        dem = self.dem_array[y][x]
        surface = self.surface[y][x]
        neighbor_surface = self.surface[ny][nx]
        if dem < neighbor_surface + self.eta < surface:
            self.surface[y][x] = neighbor_surface + self.eta
            return True
        return False

    def implement_improved_direct_filling_algorithm(self):
        self.explore_all_ascending_paths_from_the_border()
        self.scan_dem_recursively()

    def explore_all_ascending_paths_from_the_border(self):
        """Strictly upward paths from the border are first dried using tree exploration"""
        for x, y in self.whole_range_generator():
            if self._is_on_boundary(x=x, y=y):
                self.dry_upward_cell(x=x, y=y)

    def dry_upward_cell(self, x: int, y: int):
        self.depth += 1
        if self.depth > self.MAX_DEPTH:
            self.depth -= 1
            return
        for nx, ny in self.existing_neighbor_generator(x=x, y=y):
            if self._has_watered_neighbor(x=x, y=y):
                if self.convergence_operation(x=x, y=y, nx=nx, ny=ny):
                    self.dry_upward_cell(x=nx, y=ny)
        self.depth -= 1

    def _has_watered_neighbor(self, nx: int, ny: int) -> bool:
        return self.surface[ny][nx] == float("inf")

    def scan_dem_recursively(self):
        """
        improved (faster)
        to alternate scan directions,
        to reduce the depth of the dependence graph
        """
        for scan in range(8):
            y = self.y0[scan]
            x = self.x0[scan]
            something_done = False
            while True:
                if self.surface[y][x] > self.dem_array[y][x]:
                    for nx, ny in self.existing_neighbor_generator(x=x, y=y):
                        if self.convergence_operation(x=x, y=y, nx=nx, ny=ny):
                            something_done = True
                            self.dry_upward_cell(x=x, y=y)
                            break
                        elif self.did_convergence2(x=x, y=y, nx=nx, ny=ny):
                            something_done = True
                if not self.next_to_cell(x=x, y=y, index=scan):
                    break
            if something_done is False:
                return
        return self.scan_dem_recursively()


class Yamazaki2012PitFill:
    def pit_fill(self, dem_array: np.ndarray) -> np.ndarray:
        pass


class PitFillAlgorithm(NormalPitFill, Planchon2001PitFill, Yamazaki2012PitFill):
    def select_algorithm(self, algorithm: str) -> callable:
        if algorithm == "normal":
            return self.normal
        elif algorithm == "planchon_2001":
            return self.planchon_2001
        elif algorithm == "yamazaki_2012":
            return self.yamazaki_2012
        else:
            raise ValueError("algorithm must be normal, planchon_2001 or yamazaki_2012")

    def normal(self, dem_array: np.ndarray) -> np.ndarray:
        return NormalPitFill.pit_fill(self, dem_array)

    def planchon_2001(self, dem_array: np.ndarray) -> np.ndarray:
        return Planchon2001PitFill.pit_fill(self, dem_array)

    def yamazaki_2012(self, dem_array: np.ndarray) -> np.ndarray:
        return Yamazaki2012PitFill.pit_fill(self, dem_array)
