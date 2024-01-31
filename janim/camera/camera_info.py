import math
from dataclasses import dataclass, field

import numpy as np

from janim.utils.space_ops import get_norm, normalize, get_unit_normal


@dataclass
class CameraInfo:
    fov: float
    center: np.ndarray
    horizontal_vect: np.ndarray
    vertical_vect: np.ndarray

    horizontal_dist: float = field(init=False)
    vertical_dist: float = field(init=False)

    camera_location: np.ndarray = field(init=False)

    view_matrix: np.ndarray = field(init=False)
    proj_matrix: np.ndarray = field(init=False)
    frame_radius: np.ndarray = field(init=False)

    def __post_init__(self):
        self.horizontal_dist = get_norm(self.horizontal_vect)
        self.vertical_dist = get_norm(self.vertical_vect)

        self.camera_location = self._compute_camera_location()

        self.view_matrix = self._compute_view_matrix()
        self.proj_matrix = self._compute_proj_matrix()
        self.frame_radius = np.array([self.horizontal_dist, self.vertical_dist]) / 2

    @property
    def frame_size(self) -> tuple[float, float]:
        return self.horizontal_dist, self.vertical_dist

    def _compute_camera_location(self) -> np.ndarray:
        right = self.horizontal_vect
        up = self.vertical_vect
        normal = get_unit_normal(right, up)
        distance = get_norm(up) / 2 / math.tan(math.radians(self.fov / 2))
        return self.center + normal * distance

    def _compute_view_matrix(self) -> np.ndarray:
        rot_matrix = np.eye(4)
        rot_matrix[0, :3] = normalize(self.horizontal_vect)
        rot_matrix[1, :3] = normalize(self.vertical_vect)
        rot_matrix[2, :3] = normalize(self.camera_location - self.center)

        shift_matrix = np.eye(4)
        shift_matrix[:3, 3] = -self.camera_location

        return np.dot(rot_matrix, shift_matrix)

    def _compute_proj_matrix(self) -> np.ndarray:
        # TODO: avoid using QMatrix4x4

        from PySide6.QtGui import QMatrix4x4

        proj = QMatrix4x4()
        proj.setToIdentity()
        proj.perspective(self.fov, self.horizontal_dist / self.vertical_dist, 0.1, 100)

        return np.array(proj.data()).reshape((4, 4)).T
