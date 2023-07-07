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

