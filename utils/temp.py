import json
import os
from typing import Any, Literal

temp_path = "./.cache/temp.json"

os.makedirs(os.path.dirname(temp_path), exist_ok=True)
os.path.isfile(temp_path) or open(temp_path, "w").write("{}")
try:
    json.load(open(temp_path))
except json.JSONDecodeError:
    open(temp_path, "w").write("{}")


Key = Literal["restart_msg"]


def get(key: Key) -> Any:
    with open(temp_path) as file:
        data = json.load(file)
        return data.get(key)


def set(key: Key, value: Any) -> Any:
    with open(temp_path) as file:
        data = json.load(file)
    data[key] = value
    with open(temp_path, "w") as file:
        json.dump(data, file)
    return value


def delete(key: Key) -> None:
    with open(temp_path) as file:
        data = json.load(file)
    if key in data:
        del data[key]
    with open(temp_path, "w") as file:
        json.dump(data, file)


def clear() -> None:
    with open(temp_path, "w") as file:
        json.dump({}, file)
