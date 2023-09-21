import itertools as it
import numpy as np
import inspect

DEFAULT_IGNORED_LOCAL_ARGS = ['self', 'cls', 'args', 'kwargs', '__class__']

def local_kwargs(ignored_local_args: list[str] = DEFAULT_IGNORED_LOCAL_ARGS) -> dict:
    locals = inspect.currentframe().f_back.f_locals.copy()
    for arg in ignored_local_args:
        locals.pop(arg, None)
    return locals

def merge_dicts_recursively(*dicts: dict) -> dict:
    """
    Creates a dict whose keyset is the union of all the
    input dictionaries.  The value for each key is based
    on the first dict in the list with that key.

    dicts later in the list have higher priority

    When values are dictionaries, it is applied recursively
    """
    result = {}
    all_items = it.chain(*[d.items() for d in dicts])
    for key, value in all_items:
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts_recursively(result[key], value)
        else:
            result[key] = value
    return result


def soft_dict_update(d1: dict, d2: dict) -> None:
    """
    Adds key values pairs of d2 to d1 only when d1 doesn't
    already have that key
    """
    for key, value in list(d2.items()):
        if key not in d1:
            d1[key] = value


def dict_eq(d1: dict, d2: dict) -> bool:
    if len(d1) != len(d2):
        return False
    for key in d1:
        value1 = d1[key]
        value2 = d2[key]
        if type(value1) != type(value2):
            return False
        if type(d1[key]) == np.ndarray:
            if any(d1[key] != d2[key]):
                return False
        elif d1[key] != d2[key]:
            return False
    return True
