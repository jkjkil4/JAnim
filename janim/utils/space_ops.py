from __future__ import annotations
from typing import Iterable, Optional

import numpy as np
from scipy.spatial.transform import Rotation

from janim.constants import *

#region vector

def cross(v1: np.ndarray, v2: np.ndarray) -> list[np.ndarray]:
    return [
        v1[1] * v2[2] - v1[2] * v2[1],
        v1[2] * v2[0] - v1[0] * v2[2],
        v1[0] * v2[1] - v1[1] * v2[0]
    ]

def cross2d(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if len(a.shape) == 2:
        return a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    else:
        return a[0] * b[1] - b[0] * a[1]
    
def angle_of_vector(vector: np.ndarray) -> float:
    """
    Returns polar coordinate theta when vector is project on xy plane
    """
    return np.arctan2(vector[1], vector[0])

def get_norm(vect: Iterable) -> float:
    return np.sqrt(sum(x**2 for x in vect))

def normalize(vect: np.ndarray, fall_back: Optional[np.ndarray]=None) -> np.ndarray:
    norm = get_norm(vect)
    if norm > 0:
        return np.array(vect) / norm
    elif fall_back is not None:
        return fall_back
    else:
        return np.zeros(len(vect))
    
def get_unit_normal(
    v1: np.ndarray,
    v2: np.ndarray,
    tol: float = 1e-6
) -> np.ndarray:
    v1 = normalize(v1)
    v2 = normalize(v2)
    cp = cross(v1, v2)
    cp_norm = get_norm(cp)
    if cp_norm < tol:
        # Vectors align, so find a normal to them in the plane shared with the z-axis
        new_cp = cross(cross(v1, OUT), v1)
        new_cp_norm = get_norm(new_cp)
        if new_cp_norm < tol:
            return DOWN
        return new_cp / new_cp_norm
    return cp / cp_norm

def rotate_vector(
    vector: np.ndarray,
    angle: float,
    axis: np.ndarray = OUT
) -> np.ndarray:
    rot = Rotation.from_rotvec(angle * normalize(axis))
    return np.dot(vector, rot.as_matrix().T)

def find_intersection(
    p0: np.ndarray,
    v0: np.ndarray,
    p1: np.ndarray,
    v1: np.ndarray,
    threshold: float = 1e-5,
) -> np.ndarray:
    """
    Return the intersection of a line passing through p0 in direction v0
    with one passing through p1 in direction v1.  (Or array of intersections
    from arrays of such points/directions).

    For 3d values, it returns the point on the ray p0 + v0 * t closest to the
    ray p1 + v1 * t
    """
    d = len(p0.shape)
    if d == 1:
        is_3d = any(arr[2] for arr in (p0, v0, p1, v1))
    else:
        is_3d = any(z for arr in (p0, v0, p1, v1) for z in arr.T[2])
    if not is_3d:
        numer = np.array(cross2d(v1, p1 - p0))
        denom = np.array(cross2d(v1, v0))
    else:
        cp1 = cross(v1, p1 - p0)
        cp2 = cross(v1, v0)
        numer = np.array((cp1 * cp1).sum(d - 1))
        denom = np.array((cp1 * cp2).sum(d - 1))
    denom[abs(denom) < threshold] = np.inf
    ratio = numer / denom
    return p0 + (ratio * v0.T).T

#endregion

#region matrix

def rotation_matrix(angle: float, axis: np.ndarray) -> np.ndarray:
    """
    Rotation in R^3 about a specified axis of rotation.
    """
    return Rotation.from_rotvec(angle * normalize(axis)).as_matrix()

#endregion

def get_proportional_scale_size(src_width, src_height, tg_width, tg_height):
    factor1 = tg_width / src_width
    factor2 = tg_height / src_height
    factor = min(factor1, factor2)
    return src_width * factor, src_height * factor

