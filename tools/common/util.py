import json


def load_json(path: str):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def save_json(dict: dict, path: str):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(dict, file, indent=2, ensure_ascii=False)


def make_neighbor_xy(x: int, y: int, radius: int = 1, include_center: bool = False):
    for dy in range(y - radius, y + radius + 1):
        for dx in range(x - radius, x + radius + 1):
            if include_center:
                yield dx, dy
            elif not (dx == x and dy == y):
                yield dx, dy


def make_neighbor_boundary_xy(x: int, y: int, radius: int = 1):
    for ny in range(y - radius, y + radius + 1):
        for nx in range(x - radius, x + radius + 1):
            is_y_boundary = ny == y - radius or ny == y + radius
            is_x_boundary = nx == x - radius or nx == x + radius
            if is_y_boundary or is_x_boundary:
                yield nx, ny
