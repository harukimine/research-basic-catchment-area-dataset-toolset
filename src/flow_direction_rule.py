class FlowDirectionRuleMatrix:
    D8 = [
        [32, 64, 128],
        [16, 0, 1],
        [8, 4, 2],
    ]
    D16 = [
        [None, 16, None, 9, None],
        [15, 8, 1, 2, 10],
        [None, 7, 0, 3, None],
        [14, 6, 5, 4, 11],
        [None, 13, None, 12, None],
    ]


class FlowDirectionRule(FlowDirectionRuleMatrix):
    def __init__(self):
        print("init FlowDirectionRule")
        self.flow_direction_rule = "D8"
        self.flow_direction_rule_matrix: list[list[int]] = self.D8
        self.dy_range = self.set_dy_range()
        self.dx_range = self.set_dx_range()

    def set_flow_direction_rule(self, rule: str):
        self.flow_direction_rule = rule

    def set_flow_direction_rule_matrix(self):
        if self.flow_direction_rule == "D8":
            self.flow_direction_rule_matrix = self.D8
        elif self.flow_direction_rule == "D16":
            self.flow_direction_rule_matrix = self.D16
        self.set_dy_range()
        self.set_dx_range()

    def set_dy_range(self) -> range:
        y_start = (len(self.flow_direction_rule_matrix) // 2) * -1
        y_end = len(self.flow_direction_rule_matrix) // 2 + 1
        return range(y_start, y_end)

    def set_dx_range(self) -> range:
        x_start = (len(self.flow_direction_rule_matrix[0]) // 2) * -1
        x_end = len(self.flow_direction_rule_matrix[0]) // 2 + 1
        return range(x_start, x_end)

    def get_downstream_delta_xy(self, flow_direction: int) -> tuple[int, int]:
        y_start = (len(self.flow_direction_rule_matrix) // 2) * -1
        x_start = (len(self.flow_direction_rule_matrix[0]) // 2) * -1
        for y, rule_x in enumerate(self.flow_direction_rule_matrix, y_start):
            for x, rule in enumerate(rule_x, x_start):
                if rule == flow_direction:
                    return x, y

    def get_flow_direction_from_delta_xy(self, dx: int, dy: int) -> int:
        y = dy + (len(self.flow_direction_rule_matrix) // 2)
        x = dx + (len(self.flow_direction_rule_matrix[0]) // 2)
        return self.flow_direction_rule_matrix[y][x]

    def is_center(self, dx: int, dy: int) -> bool:
        if dx == 0 and dy == 0:
            return True
        else:
            return False

    def is_upstream(self, neighbor_flow_direction: int, dx: int, dy: int) -> bool:
        if self.is_center(dx, dy):
            return False
        neighbor_dx, neighbor_dy = self.get_downstream_delta_xy(neighbor_flow_direction)
        if (neighbor_dx + dx == 0) and (neighbor_dy + dy == 0):
            return True
        else:
            return False

    def is_out_of_array(self, array_shape: tuple[int, int], x: int, y: int) -> bool:
        if (0 <= y < array_shape[0]) and (0 <= x < array_shape[1]):
            return False
        else:
            return True

    def neighbor_delta_xy_generator(self, include_center=False) -> tuple[int, int]:
        for dy in self.dy_range:
            for dx in self.dx_range:
                if self.is_center(dx, dy) and not include_center:
                    continue
                yield dx, dy
