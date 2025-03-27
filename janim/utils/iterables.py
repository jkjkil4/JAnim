from __future__ import annotations

import types
import itertools as it
from typing import Callable, Iterable, Sequence, TypeVar, overload

import numpy as np

T = TypeVar("T")
S = TypeVar("S")

type ResizeFunc = Callable[[np.ndarray, int], np.ndarray]


def flatten(iterable):
    if not isinstance(iterable, Iterable):
        return [iterable]
    return list(it.chain.from_iterable(flatten(x) for x in iterable))


def remove_list_redundancies(lst: Iterable[T]) -> list[T]:
    """
    Used instead of list(set(l)) to maintain order
    Keeps the last occurrence of each element
    """
    reversed_result = []
    used = set()
    for x in reversed(lst):
        if x not in used:
            reversed_result.append(x)
            used.add(x)
    reversed_result.reverse()
    return reversed_result


def list_update(l1: Iterable[T], l2: Iterable[T]) -> list[T]:
    """
    Used instead of list(set(l1).update(l2)) to maintain order,
    making sure duplicates are removed from l1, not l2.
    """
    return [e for e in l1 if e not in l2] + list(l2)


def list_difference_update(l1: Iterable[T], l2: Iterable[T]) -> list[T]:
    return [e for e in l1 if e not in l2]


def adjacent_n_tuples(objects: Iterable[T], n: int) -> zip[tuple[T, T]]:
    return zip(*[
        [*objects[k:], *objects[:k]]
        for k in range(n)
    ])


def adjacent_pairs(objects: Iterable[T]) -> zip[tuple[T, T]]:
    return adjacent_n_tuples(objects, 2)


def batch_by_property(
    items: Iterable[T],
    property_func: Callable[[T], S]
) -> list[tuple[T, S]]:
    """
    Takes in a list, and returns a list of tuples, (batch, prop)
    such that all items in a batch have the same output when
    put into property_func, and such that chaining all these
    batches together would give the original list (i.e. order is
    preserved)
    """
    batch_prop_pairs = []
    curr_batch = []
    curr_prop = None
    for item in items:
        prop = property_func(item)
        if prop != curr_prop:
            # Add current batch
            if len(curr_batch) > 0:
                batch_prop_pairs.append((curr_batch, curr_prop))
            # Redefine curr
            curr_prop = prop
            curr_batch = [item]
        else:
            curr_batch.append(item)
    if len(curr_batch) > 0:
        batch_prop_pairs.append((curr_batch, curr_prop))
    return batch_prop_pairs


def listify(obj) -> list:
    if isinstance(obj, str):
        return [obj]
    try:
        return list(obj)
    except TypeError:
        return [obj]


def resize_array(nparray: np.ndarray, length: int) -> np.ndarray:
    if len(nparray) == length:
        return nparray
    return np.resize(nparray, (length, *nparray.shape[1:]))


@overload
def resize_preserving_order(array: np.ndarray, length: int) -> np.ndarray: ...
@overload
def resize_preserving_order[T](array: list[T], length: int, fall_back: Callable = types.NoneType) -> list[T]: ...


def resize_preserving_order(
    array: np.ndarray | list,
    length: int,
    fall_back: Callable = types.NoneType
):
    if isinstance(array, np.ndarray):
        if len(array) == 0:
            return np.zeros((0, *array.shape[1:]), dtype=array.dtype)
        if len(array) == length:
            return array
        indices = np.arange(length) * len(array) // length
        return array[indices]

    else:  # not isinstance(array, np.ndarray)
        if len(array) == 0:
            return [fall_back() for _ in range(length)]
        if len(array) == length:
            return array
        indices = np.arange(length) * len(array) // length
        return [array[idx] for idx in indices]


def resize_preserving_order_indice_groups(len1: int, len2: int) -> list[list[int]]:
    indices = np.arange(len2) * len1 // len2
    result = []
    prev = 0
    current = []
    for i, indice in enumerate(indices):
        if prev != indice:
            prev = indice
            result.append(current)
            current = []

        current.append(i)

    result.append(current)

    return result


def resize_preserving_head_and_tail(
    array: np.ndarray,
    length: int
):
    indices = np.round(np.linspace(0, len(array) - 1, length)).astype(int)
    if len(array) == 0:
        return np.zeros((0, *array.shape[1:]), dtype=array.dtype)
    if len(array) == length:
        return array
    return array[indices]


def resize_and_repeatedly_extend(
    array: np.ndarray,
    length: int,
    fall_back: Callable[[int], np.ndarray] = lambda length: np.zeros((length, 3))
) -> np.ndarray:
    '''
    注意：这个函数在 length <= len(array) 时，不会产生 array 的拷贝
    '''
    if length == len(array):
        return array

    if length < len(array):
        return array[:length]

    elif length > len(array):
        if len(array) == 0:
            return fall_back(length)

        # len(array) != 0
        return np.vstack([
            array,
            np.repeat([array[-1]], length - len(array), axis=0)
        ])


def resize_with_interpolation(nparray: np.ndarray, length: int) -> np.ndarray:
    nparray = np.asarray(nparray)
    if len(nparray) == length:
        return nparray
    if length == 0:
        return np.zeros((0, *nparray.shape[1:]), dtype=nparray.dtype)
    if len(nparray) == 1:
        return np.repeat(nparray, length, axis=0)
    cont_indices = np.linspace(0, len(nparray) - 1, length, dtype=nparray.dtype)
    lh_s = cont_indices.astype(int)
    rh_s = np.ceil(cont_indices).astype(int)
    a_s = cont_indices % 1
    a_s = np.expand_dims(a_s, axis=tuple(range(1, nparray.ndim)))
    return (1 - a_s) * nparray[lh_s] + a_s * nparray[rh_s]


def make_even(
    iterable_1: Sequence[T],
    iterable_2: Sequence[S]
) -> tuple[list[T], list[S]]:
    len1 = len(iterable_1)
    len2 = len(iterable_2)
    if len1 == len2:
        return iterable_1, iterable_2
    new_len = max(len1, len2)
    return (
        [iterable_1[(n * len1) // new_len] for n in range(new_len)],
        [iterable_2[(n * len2) // new_len] for n in range(new_len)]
    )


def hash_obj(obj: object) -> int:
    if isinstance(obj, dict):
        new_obj = {k: hash_obj(v) for k, v in obj.items()}
        return hash(tuple(frozenset(sorted(new_obj.items()))))

    if isinstance(obj, (set, tuple, list)):
        return hash(tuple(hash_obj(e) for e in obj))

    return hash(obj)
