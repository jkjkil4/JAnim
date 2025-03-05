from dataclasses import dataclass
from typing import Callable

METHOD_UPDATER_KEY = '__methodupdater_meta'


@dataclass
class MethodUpdaterInfo:
    updater: Callable
    grouply: bool


def register_updater(updater: Callable, *, grouply: bool = False):
    def wrapper(func):
        setattr(func, METHOD_UPDATER_KEY, MethodUpdaterInfo(updater, grouply))
        return func
    return wrapper
