from __future__ import annotations

from typing import Iterable, Self

import numpy as np
from pyquaternion import Quaternion

import janim.utils.refresh as refresh
from janim.camera.camera_info import CameraInfo
from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.constants import ORIGIN, OUT
from janim.items.points import Points
from janim.typing import Vect
from janim.utils.bezier import interpolate
from janim.utils.config import Config
from janim.utils.paths import PathFunc, straight_path
from janim.utils.simple_functions import clip


class Cmpt_CameraPoints[ItemT](Cmpt_Points[ItemT]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset()

    def reset(self) -> Self:
        '''
        将摄像机几何属性设置为初始状态
        '''
        self.orig_height = Config.get.frame_height

        self.set([ORIGIN])
        self.size = [Config.get.frame_width, Config.get.frame_height]
        self.fov = 45
        self.orientation = Quaternion()     # 单位四元数

        return self

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy._size = self._size.copy()
        cmpt_copy.orientation = Quaternion(self.orientation.elements)
        return cmpt_copy

    def become(self, other: Cmpt_CameraPoints) -> Self:
        self.set(other.get())
        self.size = other.size
        self.fov = other.fov
        self.orientation = Quaternion(other.orientation.elements)

        return self

    def not_changed(self, other: Cmpt_CameraPoints) -> Self:
        if not super().not_changed(other):
            return False
        if np.any(self.size != other.size) or self.fov != other.fov:
            return False
        return np.isclose(self.orientation.elements, other.orientation.elements).all()

    def interpolate(
        self,
        cmpt1: Self,
        cmpt2: Self,
        alpha: float,
        *,
        path_func: PathFunc = straight_path
    ) -> None:
        alpha = clip(alpha, 0, 1)

        super().interpolate(cmpt1, cmpt2, alpha)
        self.size = interpolate(cmpt1.size, cmpt2.size, alpha)
        self.fov = interpolate(cmpt1.fov, cmpt2.fov, alpha)
        self.orientation = Quaternion.slerp(cmpt1.orientation, cmpt2.orientation, amount=alpha)

    @property
    def scaled_factor(self) -> float:
        return self.size[1] / self.orig_height

    @property
    def size(self) -> np.ndarray:
        return self._size

    @size.setter
    def size(self, value: Vect) -> None:
        self._size = np.array(value, dtype=np.float64)
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
        *,
        about_point: Vect | None = None,
        about_edge: Vect = ORIGIN,
        **kwargs
    ) -> Self:
        '''
        将摄像机缩放指定倍数
        '''
        if about_point is not None or about_edge is not ORIGIN:
            if about_point is None:
                rot_mat_T = self.orientation.rotation_matrix.T
                width, height = self.size
                vect = np.array([width / 2, height / 2, 0]) * np.sign(about_edge)
                vect @= rot_mat_T
                about_point = self.get()[0] + vect

            new_center = (self.get()[0] - about_point) * scale_factor + about_point
            self.set([new_center])

        self._size *= scale_factor

        return self

    def rotate(
        self,
        angle: float,
        *,
        axis: Vect = OUT,
        absolute: bool = True,
        **kwargs
    ) -> Self:
        '''
        将摄像机绕 ``axis`` 轴进行旋转

        - 默认 ``absolute=True`` 表示绕全局坐标系旋转
        - ``absolute=False`` 表示绕相机自身坐标系旋转，并且此时 ``about_point`` 参数无效
        '''
        q_rot = Quaternion(axis=axis, angle=angle)
        if absolute:
            super().rotate(angle, axis=axis, **kwargs)
            self.orientation = q_rot * self.orientation
        else:
            self.orientation *= q_rot

        return self

    @property
    @Cmpt_Points.set.self_refresh
    @refresh.register
    def info(self) -> CameraInfo:
        '''
        摄像机的几何属性
        '''
        rot_mat_T = self.orientation.rotation_matrix.T
        width, height = self.size
        return CameraInfo(
            self.scaled_factor,
            self.fov,
            self.get()[0],
            np.array([width, 0, 0]) @ rot_mat_T,
            np.array([0, height, 0]) @ rot_mat_T
        )


class Camera(Points):
    points = CmptInfo(Cmpt_CameraPoints[Self])
