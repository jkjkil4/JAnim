from __future__ import annotations

from typing import Iterable, Self

import numpy as np
from scipy.spatial.transform import Rotation, Slerp

import janim.utils.refresh as refresh
from janim.camera.camera_info import CameraInfo
from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.constants import ORIGIN, OUT
from janim.items.points import Points
from janim.typing import Vect
from janim.utils.bezier import interpolate
from janim.utils.config import Config
from janim.utils.space_ops import normalize


class Cmpt_CameraPoints(Cmpt_Points):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset()

    def reset(self) -> Self:
        '''
        将摄像机几何属性设置为初始状态
        '''
        self.set([ORIGIN])
        self.size = [Config.get.frame_width, Config.get.frame_height]
        self.fov = 45
        self.orientation = Rotation.identity()

        return self

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy._size = self._size.copy()
        cmpt_copy.orientation = self.orientation.from_quat(self.orientation.as_quat())
        return cmpt_copy

    def __eq__(self, other: Cmpt_CameraPoints) -> Self:
        if not super().__eq__(other):
            return False
        if np.any(self.size != other.size) or self.fov != other.fov:
            return False
        return np.all(self.orientation.as_quat() == other.orientation.as_quat())

    def interpolate(self, cmpt1: Self, cmpt2: Self, alpha: float) -> None:
        super().interpolate(cmpt1, cmpt2, alpha)
        self.fov = interpolate(cmpt1.fov, cmpt2.fov, alpha)
        self.orientation = Slerp([0, 1], Rotation.concatenate([cmpt1.orientation, cmpt2.orientation]))(alpha)

    @property
    def size(self) -> np.ndarray:
        return self._size

    @size.setter
    def size(self, value: Vect) -> None:
        self._size = np.array(value)
        self.mark_refresh(Cmpt_CameraPoints.info.fget)

    @property
    def fov(self) -> float:
        return self._fov

    @fov.setter
    def fov(self, val: float) -> None:
        self._fov = val
        self.mark_refresh(Cmpt_CameraPoints.info.fget)

    def scale(
        self,
        scale_factor: float | Iterable,
        **kwargs
    ) -> Self:
        '''
        将摄像机缩放指定倍数
        '''
        self._size *= scale_factor

    def rotate(
        self,
        angle: float,
        *,
        axis: Vect = OUT,
        **kwargs
    ) -> Self:
        '''
        将摄像机绕 ``axis`` 轴进行旋转
        '''
        super().rotate(angle, axis=axis, **kwargs)
        self.orientation *= Rotation.from_rotvec(angle * normalize(axis))
        return self

    @property
    @Cmpt_Points.set.self_refresh()
    @refresh.register
    def info(self) -> CameraInfo:
        '''
        摄像机的几何属性
        '''
        rot_mat_T = self.orientation.as_matrix().T
        width, height = self.size
        return CameraInfo(
            self.fov,
            self.self_box.center,
            np.dot(np.array([width, 0, 0]), rot_mat_T),
            np.dot(np.array([0, height, 0]), rot_mat_T)
        )


class Camera(Points):
    points = CmptInfo(Cmpt_CameraPoints)
