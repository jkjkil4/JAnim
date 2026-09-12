from __future__ import annotations

from typing import Iterable, Self

import numpy as np
from janim_backend.math import Quaternion

from janim.camera.camera_info import CameraInfo
from janim.components.core.attrs import ComponentAttrs
from janim.components.core.component import CmptInfo
from janim.components.impls.points import Cmpt_Points
from janim.constants import ORIGIN, OUT
from janim.items.points import Points
from janim.typing import Vect, VectArray
from janim.utils.bezier import interpolate
from janim.utils.cmpt_lazy import cmpt_lazy_method
from janim.utils.config import Config
from janim.utils.paths import PathFunc, straight_path
from janim.utils.simple_functions import clip
from janim.utils.space_ops import quat_from_angle_axis


class Cmpt_CameraPoints[ItemT](Cmpt_Points[ItemT]):
    _attrs = ComponentAttrs()

    orig_height = _attrs.float()
    size = _attrs.direct_object(tuple[float, float], nullable=False)
    fov = _attrs.float()
    orientation = _attrs.direct_object(Quaternion, nullable=False)

    @size.on_modified
    @fov.on_modified
    @orientation.on_modified
    def _on_modified(self) -> None:
        if self._bind is not None:
            self._bind.reset_computed_for_func(Cmpt_CameraPoints.info.fget)  # type: ignore

    def __cmpt_init__(self) -> None:
        self.reset()

    def set(
        self,
        points: VectArray | None = None,
        *,
        size: Vect | None = None,
        fov: float | None = None,
        orientation: Quaternion | None = None,
    ) -> Self:
        """
        设置摄像机位置以及有关属性

        -   ``points``: 点集，必须只有一个点，表示摄像机中心位置

            另见 :meth:`~.Cmpt_Points.shift` :meth:`~.Cmpt_Points.move_to`

        -   ``size``: 摄像机视窗大小，格式为 ``[width, height]``

            另见 :meth:`~.Cmpt_CameraPoints.scale`

        -   ``fov``: 摄像机视野角度，单位为度

        -   ``orientation``: 摄像机朝向，四元数表示

            另见 :meth:`~.Cmpt_CameraPoints.rotate`
        """
        if points is not None:
            points = np.asarray(points)
            assert points.ndim == 2
            assert points.shape[0] == 1

            super().set(points)

        if size is not None:
            self.size = size
        if fov is not None:
            self.fov = fov
        if orientation is not None:
            self.orientation = orientation

        return self

    def reset(self) -> Self:
        """
        将摄像机几何属性设置为初始状态
        """
        self.orig_height = Config.get.frame_height

        self.set([ORIGIN])
        self.size = (Config.get.frame_width, Config.get.frame_height)
        self.fov = 45
        self.orientation = Quaternion.identity()

        return self

    def interpolate(  # type: ignore
        self,
        cmpt1: Cmpt_CameraPoints,
        cmpt2: Cmpt_CameraPoints,
        alpha: float,
        *,
        path_func: PathFunc = straight_path,
    ) -> None:
        alpha = clip(alpha, 0, 1)

        super().interpolate(cmpt1, cmpt2, alpha)
        self.size = (
            interpolate(cmpt1.size[0], cmpt2.size[0], alpha),
            interpolate(cmpt1.size[1], cmpt2.size[1], alpha),
        )
        self.fov = interpolate(cmpt1.fov, cmpt2.fov, alpha)
        self.orientation = cmpt1.orientation.slerp(cmpt2.orientation, alpha)

    @property
    def scaled_factor(self) -> float:
        return self.size[1] / self.orig_height

    def scale(
        self,
        scale_factor: float | Iterable,
        *,
        about_point: Vect | None = None,
        about_edge: Vect = ORIGIN,
        **kwargs,
    ) -> Self:
        """
        将摄像机缩放指定倍数
        """
        if about_point is not None or about_edge is not ORIGIN:
            if about_point is None:
                rot_mat_T = self.orientation.rotation_matrix.T
                width, height = self.size
                vect = np.array([width / 2, height / 2, 0]) * np.sign(about_edge)
                vect @= rot_mat_T
                about_point = self.get()[0] + vect

            new_center = (self.get()[0] - about_point) * scale_factor + about_point
            self.set([new_center])

        self.size = tuple(np.asarray(self.size) * scale_factor)

        return self

    def rotate(
        self,
        angle: float,
        *,
        axis: Vect = OUT,
        absolute: bool = True,
        **kwargs,
    ) -> Self:
        """
        将摄像机绕 ``axis`` 轴进行旋转

        - 默认 ``absolute=True`` 表示绕全局坐标系旋转
        - ``absolute=False`` 表示绕相机自身坐标系旋转，并且此时 ``about_point`` 参数无效
        """
        q_rot = quat_from_angle_axis(angle, axis)
        if absolute:
            # 如果没有后代物件（一般也不会有，谁这么闲给摄像机设置后代物件）
            # 则没必要调用 super().rotate() 了，可以快很多
            if self._bind is not None and self._bind.at_item.has_child():
                super().rotate(angle, axis=axis, **kwargs)
            self.orientation = q_rot * self.orientation
        else:
            self.orientation = self.orientation * q_rot

        return self

    @property
    @Cmpt_Points.set.self_refresh
    @cmpt_lazy_method
    def info(self) -> CameraInfo:
        """
        摄像机的几何属性
        """
        rot_mat_T = self.orientation.rotation_matrix.T
        width, height = self.size
        return CameraInfo(
            self.scaled_factor,
            self.fov,
            self.get()[0],
            (np.array([width, 0, 0]) @ rot_mat_T).astype(np.float32),
            (np.array([0, height, 0]) @ rot_mat_T).astype(np.float32),
        )


class Camera(Points):
    points = CmptInfo(Cmpt_CameraPoints[Self])

    def apply_style(
        self,
        size: Vect | None = None,
        fov: float | None = None,
        orientation: Quaternion | None = None,
        **kwargs,
    ) -> Self:
        self.points.set(size=size, fov=fov, orientation=orientation)
        return super().apply_style(**kwargs)
