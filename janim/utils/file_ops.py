import importlib.util
import os


def get_janim_dir() -> str:
    return os.path.dirname(importlib.util.find_spec('janim').origin)


def readall(filepath: str) -> str:
    with open(filepath, 'rt') as f:
        return f.read()
