import json


def load_json(path: str):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def save_json(dict: dict, path: str):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(dict, file, indent=2, ensure_ascii=False)


def make_neighbor_generator(radius: int = 1, include_center: bool = False):
    for ny in range(-radius, radius + 1):
        for nx in range(-radius, radius + 1):
            if nx == 0 and ny == 0 and include_center is False:
                continue
            yield nx, ny
