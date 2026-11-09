import json
from pathlib import Path
from typing import Any, Literal

TEMP_PATH = Path(".cache/temp.json")

TEMP_PATH.parent.mkdir(parents=True, exist_ok=True)
try:
    with open(TEMP_PATH) as file:
        json.load(file)
except FileNotFoundError, json.JSONDecodeError:
    with open(TEMP_PATH, "w") as file:
        file.write("{}")


Key = Literal["restart_msg"]


def get(key: Key) -> Any:
    with open(TEMP_PATH) as file:
        data = json.load(file)
        return data.get(key)


def set(key: Key, value: Any) -> Any:
    with open(TEMP_PATH) as file:
        data = json.load(file)
    data[key] = value
    with open(TEMP_PATH, "w") as file:
        json.dump(data, file)
    return value


def delete(key: Key) -> None:
    with open(TEMP_PATH) as file:
        data = json.load(file)
    if key in data:
        del data[key]
    with open(TEMP_PATH, "w") as file:
        json.dump(data, file)


def clear() -> None:
    with open(TEMP_PATH, "w") as file:
        json.dump({}, file)
