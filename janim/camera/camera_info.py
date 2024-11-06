import math
from dataclasses import dataclass, field

import numpy as np

from janim.utils.space_ops import get_norm, normalize, get_unit_normal
from janim.typing import VectArray


@dataclass
class CameraInfo:
    scaled_factor: float

    fov: float
    center: np.ndarray
    horizontal_vect: np.ndarray
    vertical_vect: np.ndarray

    horizontal_dist: float = field(init=False)
    vertical_dist: float = field(init=False)

    distance_from_plane: float = field(init=False)
    fixed_distance_from_plane: float = field(init=False)

    camera_location: np.ndarray = field(init=False)

    view_matrix: np.ndarray = field(init=False)
    proj_matrix: np.ndarray = field(init=False)
    proj_view_matrix: np.ndarray = field(init=False)
    frame_radius: np.ndarray = field(init=False)

    def __post_init__(self):
        self.horizontal_dist = get_norm(self.horizontal_vect)
        self.vertical_dist = get_norm(self.vertical_vect)

        self.distance_from_plane = self._compute_distance_from_plane(self.vertical_dist)
        self.fixed_distance_from_plane = self._compute_distance_from_plane(self.vertical_dist / self.scaled_factor)

        self.camera_location = self._compute_camera_location()

        self.view_matrix = self._compute_view_matrix()
        self.proj_matrix = self._compute_proj_matrix()
        self.proj_view_matrix = self.proj_matrix @ self.view_matrix
        self.frame_radius = np.array([self.horizontal_dist, self.vertical_dist]) / 2

    @property
    def frame_size(self) -> tuple[float, float]:
        return self.horizontal_dist, self.vertical_dist

    def map_points(self, points: VectArray) -> np.ndarray:
        n = len(points)
        aligned = np.empty((n, 4))
        aligned[:, :3] = points
        aligned[:, -1] = 1
        mapped = aligned @ self.proj_view_matrix.T
        return mapped[:, :2] / mapped[:, 3][:, np.newaxis]

    def map_fixed_in_frame_points(self, points: VectArray) -> np.ndarray:
        n = len(points)
        aligned = np.empty((n, 4))
        aligned[:, :3] = points
        aligned[:, :3] -= [0, 0, self.fixed_distance_from_plane]
        aligned[:, -1] = 1
        mapped = aligned @ self.proj_matrix.T
        return mapped[:, :2] / mapped[:, 3][:, np.newaxis]

    def _compute_distance_from_plane(self, vertical_length: float) -> float:
        return vertical_length / 2 / math.tan(math.radians(self.fov / 2))

    def _compute_camera_location(self) -> np.ndarray:
        right = self.horizontal_vect
        up = self.vertical_vect
        normal = get_unit_normal(right, up)
        return self.center + normal * self.distance_from_plane

    def _compute_view_matrix(self) -> np.ndarray:
        rot_matrix = np.eye(4)
        rot_matrix[0, :3] = normalize(self.horizontal_vect)
        rot_matrix[1, :3] = normalize(self.vertical_vect)
        rot_matrix[2, :3] = normalize(self.camera_location - self.center)

        shift_matrix = np.eye(4)
        shift_matrix[:3, 3] = -self.camera_location

        return rot_matrix @ shift_matrix

    def _compute_proj_matrix(self, near=0.1, far=100.0) -> np.ndarray:
        aspect = self.horizontal_dist / self.vertical_dist

        f = 1.0 / np.tan(np.radians(self.fov) / 2.0)
        return np.array([
            [f / aspect, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (far + near) / (near - far), 2 * far * near / (near - far)],
            [0, 0, -1, 0]
        ])
