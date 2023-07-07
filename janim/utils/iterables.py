import numpy as np

def resize_array(nparray: np.ndarray, length: int) -> np.ndarray:
    if len(nparray) == length:
        return nparray
    return np.resize(nparray, (length, *nparray.shape[1:]))

def resize_preserving_order(nparray: np.ndarray, length: int) -> np.ndarray:
    if len(nparray) == 0:
        return np.zeros((length, *nparray.shape[1:]))
    if len(nparray) == length:
        return nparray
    indices = np.arange(length) * len(nparray) // length
    return nparray[indices]

def resize_with_interpolation(nparray: np.ndarray, length: int) -> np.ndarray:
    if len(nparray) == length:
        return nparray
    if length == 0:
        return np.zeros((0, *nparray.shape[1:]))
    cont_indices = np.linspace(0, len(nparray) - 1, length)
    return np.array([
        (1 - a) * nparray[lh] + a * nparray[rh]
        for ci in cont_indices
        for lh, rh, a in [(int(ci), int(np.ceil(ci)), ci % 1)]
    ])
