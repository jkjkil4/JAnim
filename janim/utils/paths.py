import math
from typing import Callable

import numpy as np

from janim.constants import OUT
from janim.utils.bezier import interpolate
from janim.utils.space_ops import get_norm
from janim.utils.space_ops import rotation_matrix_transpose

STRAIGHT_PATH_THRESHOLD = 0.01

type PathFunc = Callable[[np.ndarray, np.ndarray, float], np.ndarray]


def straight_path(
    start_points: np.ndarray,
    end_points: np.ndarray,
    alpha: float
) -> np.ndarray:
    """
    Same function as interpolate, but renamed to reflect
    intent of being used to determine how a set of points move
    to another set.  For instance, it should be a specific case
    of path_along_arc
    """
    return interpolate(start_points, end_points, alpha)


def path_along_arc(
    arc_angle: float,
    axis: np.ndarray = OUT
) -> Callable[[np.ndarray, np.ndarray, float], np.ndarray]:
    """
    If vect is vector from start to end, [vect[:,1], -vect[:,0]] is
    perpendicular to vect in the left direction.
    """
    if abs(arc_angle) < STRAIGHT_PATH_THRESHOLD:
        return straight_path
    if get_norm(axis) == 0:
        axis = OUT
    unit_axis = axis / get_norm(axis)

    def path(start_points, end_points, alpha):
        vects = end_points - start_points
        centers = start_points + 0.5 * vects
        if arc_angle != np.pi:
            centers += np.cross(unit_axis, vects / 2.0) / math.tan(arc_angle / 2)
        rot_matrix_T = rotation_matrix_transpose(alpha * arc_angle, unit_axis)
        return centers + np.dot(start_points - centers, rot_matrix_T)

    return path


def clockwise_path() -> Callable[[np.ndarray, np.ndarray, float], np.ndarray]:
    return path_along_arc(-np.pi)


def counterclockwise_path() -> Callable[[np.ndarray, np.ndarray, float], np.ndarray]:
    return path_along_arc(np.pi)
