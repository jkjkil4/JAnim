import math
from dataclasses import dataclass, field

import numpy as np

from janim.utils.space_ops import get_norm, normalize, get_unit_normal
from janim.typing import VectArray


@dataclass
class CameraInfo:
    """
    摄像机属性

    可以通过 :attr:`~.Cmpt_CameraPoints.info` 得到
    """

    scaled_factor: float
    """
    摄像机相比默认尺寸的缩放比率，视野越大，该值越大，反之同理
    """

    fov: float
    """
    摄像机在竖直方向的视场角
    """

    center: np.ndarray
    """
    摄像机取景框的中心（默认位置下即为原点）
    """

    horizontal_vect: np.ndarray
    """
    摄像机水平向量，在视野中从左指向右
    """

    vertical_vect: np.ndarray
    """
    摄像机竖直向量，在视野中从下指向上
    """

    horizontal_dist: float = field(init=False)
    """
    摄像机取景框在水平方向的宽度
    """

    vertical_dist: float = field(init=False)
    """
    摄像机取景框在竖直方向的宽度
    """

    distance_from_plane: float = field(init=False)
    """
    摄像机观察点距离取景框的距离
    """

    fixed_distance_from_plane: float = field(init=False)
    """
    摄像机在默认尺寸下观察点距离取景框的距离
    """

    camera_location: np.ndarray = field(init=False)
    """
    摄像机观察点的位置
    """

    view_matrix: np.ndarray = field(init=False)
    """
    观察矩阵
    """

    proj_matrix: np.ndarray = field(init=False)
    """
    投影矩阵
    """

    proj_view_matrix: np.ndarray = field(init=False)
    """
    投影矩阵和观察矩阵的复合
    """

    frame_radius: np.ndarray = field(init=False)
    """
    摄像机取景框在水平与竖直方向上的半径（宽度的一半）
    """

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
        """
        摄像机取景框在水平与竖直方向的宽度
        """
        return (self.horizontal_dist, self.vertical_dist)

    @property
    def camera_axis(self) -> np.ndarray:
        """
        摄像机中心轴，即摄像机朝向的反方向，从取景框中心指向观察点的向量
        """
        return self.camera_location - self.center

    def map_points(self, points: VectArray) -> np.ndarray:
        """
        将空间中的点映射到摄像机取景框的 GL 坐标（``-1`` ~ ``1``）中

        返回二维坐标序列
        """
        n = len(points)
        aligned = np.empty((n, 4))
        aligned[:, :3] = points
        aligned[:, -1] = 1
        mapped = aligned @ self.proj_view_matrix.T
        return mapped[:, :2] / mapped[:, 3][:, np.newaxis]

    def map_points_with_depth(self, points: VectArray) -> np.ndarray:
        """
        将空间中的点映射到摄像机取景框的 GL 坐标（``-1`` ~ ``1``）中

        返回三维坐标序列，与 :meth:`map_points` 相比，最后一个分量带有深度信息
        """
        n = len(points)
        aligned = np.empty((n, 4))
        aligned[:, :3] = points
        aligned[:, -1] = 1
        mapped = aligned @ self.proj_view_matrix.T
        return mapped[:, :3] / mapped[:, 3][:, np.newaxis]

    def map_fixed_in_frame_points(self, points: VectArray) -> np.ndarray:
        """
        将空间中的点映射到默认摄像机取景框的 GL 坐标（``-1`` ~ ``1``）中

        返回二维坐标序列
        """
        n = len(points)
        aligned = np.empty((n, 4))
        aligned[:, :3] = points
        aligned[:, :3] -= [0, 0, self.fixed_distance_from_plane]
        aligned[:, -1] = 1
        mapped = aligned @ self.proj_matrix.T
        return mapped[:, :2] / mapped[:, 3][:, np.newaxis]

    def map_fixed_in_frame_points_with_depth(self, points: VectArray) -> np.ndarray:
        """
        将空间中的点映射到默认摄像机取景框的 GL 坐标（``-1`` ~ ``1``）中

        返回三维坐标序列，与 :meth:`map_fixed_in_frame_points` 相比，最后一个分量带有深度信息
        """
        n = len(points)
        aligned = np.empty((n, 4))
        aligned[:, :3] = points
        aligned[:, :3] -= [0, 0, self.fixed_distance_from_plane]
        aligned[:, -1] = 1
        mapped = aligned @ self.proj_matrix.T
        return mapped[:, :3] / mapped[:, 3][:, np.newaxis]

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
        rot_matrix[2, :3] = normalize(self.camera_axis)

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
