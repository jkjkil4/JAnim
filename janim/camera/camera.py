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
from janim.utils.paths import PathFunc, straight_path
from janim.utils.simple_functions import clip
from janim.utils.space_ops import normalize


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
        self.orientation = Rotation.identity()

        return self

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy._size = self._size.copy()
        cmpt_copy.orientation = self.orientation.from_quat(self.orientation.as_quat())
        return cmpt_copy

    def become(self, other: Cmpt_CameraPoints) -> Self:
        self.set(other.get())
        self.size = other.size
        self.fov = other.fov
        # 有无更好的复制方法？
        self.orientation = Rotation.from_rotvec(other.orientation.as_rotvec())

        return self

    def not_changed(self, other: Cmpt_CameraPoints) -> Self:
        if not super().not_changed(other):
            return False
        if np.any(self.size != other.size) or self.fov != other.fov:
            return False
        return np.isclose(self.orientation.as_quat(), other.orientation.as_quat()).all()

    def interpolate(
        self,
        cmpt1: Self,
        cmpt2: Self,
        alpha: float,
        *,
        path_func: PathFunc = straight_path
    ) -> None:
        # 下面对 Slerp 的调用有次出现了 ValueError: Interpolation times must be within the range [0, 1], both inclusive.
        # 所以这里限制一下 alpha（本来我觉得没必要的，但是为什么会有上面这个报错呢）
        alpha = clip(alpha, 0, 1)

        super().interpolate(cmpt1, cmpt2, alpha)
        self.size = interpolate(cmpt1.size, cmpt2.size, alpha)
        self.fov = interpolate(cmpt1.fov, cmpt2.fov, alpha)
        self.orientation = Slerp([0, 1], Rotation.concatenate([cmpt1.orientation, cmpt2.orientation]))(alpha)

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
        **kwargs
    ) -> Self:
        '''
        将摄像机缩放指定倍数
        '''
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
        if absolute:
            super().rotate(angle, axis=axis, **kwargs)
            self.orientation = Rotation.from_rotvec(angle * normalize(axis)) * self.orientation
        else:
            self.orientation *= Rotation.from_rotvec(angle * normalize(axis))

        return self

    @property
    @Cmpt_Points.set.self_refresh
    @refresh.register
    def info(self) -> CameraInfo:
        '''
        摄像机的几何属性
        '''
        rot_mat_T = self.orientation.as_matrix().T
        width, height = self.size
        return CameraInfo(
            self.scaled_factor,
            self.fov,
            self.self_box.center,
            np.array([width, 0, 0]) @ rot_mat_T,
            np.array([0, height, 0]) @ rot_mat_T
        )


class Camera(Points):
    points = CmptInfo(Cmpt_CameraPoints[Self])
