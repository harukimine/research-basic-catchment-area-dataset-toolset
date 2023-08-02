import json


def load_json(path: str):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def save_json(dict: dict, path: str):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(dict, file, indent=2, ensure_ascii=False)
