from typing import Self

import janim.utils.refresh as refresh
from janim.camera.camera_info import CameraInfo
from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.constants import ORIGIN
from janim.items.points import Points
from janim.utils.config import Config
from janim.utils.signal import Signal


class Cmpt_CameraPoints(Cmpt_Points):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset()

    def copy(self) -> Self:
        return super().copy()

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

    def reset(self):
        self.fov = 45
        self.set([ORIGIN,
                  Config.get.left_side, Config.get.right_side,
                  Config.get.bottom, Config.get.top])
        return self

    @property
    def fov(self) -> float:
        return self._fov

    @fov.setter
    @Signal
    def fov(self, val: float):
        self._fov = val
        Cmpt_CameraPoints.fov.fset.emit(self)

    @property
    @fov.fset.self_refresh()
    @refresh.register
    def info(self) -> CameraInfo:
        points = self.get()
        return CameraInfo(self.fov, points[0], points[2] - points[1], points[4] - points[3])


class Camera(Points):
    points = CmptInfo(Cmpt_CameraPoints)
