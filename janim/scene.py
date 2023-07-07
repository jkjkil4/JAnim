from __future__ import annotations
from typing import List
import itertools as it

from PySide6.QtGui import QMatrix4x4, QVector3D

from janim.items.item import Item, MethodGroup
from janim.utils.math_functions import get_unit_normal, get_proportional_scale_size
from janim.constants import *
from janim.shaders.render import RenderData

class Scene:
    def __init__(self) -> None:
        self.camera = Camera()

        # relation
        self.items: List[Item] = []

    #region 基本结构

    def __getitem__(self, value) -> Item | MethodGroup:
        if isinstance(value, slice):
            return MethodGroup(*self.items[value])
        return self.items[value]

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def add(self, *items: Item) -> Scene:
        for item in items:
            if item in self:
                continue
            if item.parent:
                item.parent.remove(item)
            self.items.append(item)
            item.parent = self
        return self

    def remove(self, *items: Item) -> Scene:
        for item in items:
            if item not in self:
                continue
            item.parent = None
            self.items.remove(item)
        return self
    
    def get_family(self) -> List[Item]:
        return list(it.chain(*(item.get_family() for item in self.items)))
    
    #endregion

    def render(self) -> None:
        data = RenderData(
            self.camera.compute_view_matrix(),
            self.camera.compute_wnd_mul_proj_matrix()
        )

        for item in self:
            item.render(data)

class Camera(Item):
    frame_shape = (FRAME_WIDTH, FRAME_HEIGHT)
    window_shape = (1920, 1080)
    center_point = ORIGIN

    def __init__(self) -> None:
        super().__init__()

        self.fov = 45
        self.set_points([ORIGIN, LEFT_SIDE, RIGHT_SIDE, BOTTOM, TOP])

    def compute_view_matrix(self) -> QMatrix4x4:
        center = self.points[0]
        hor = self.points[2] - self.points[1]
        ver = self.points[4] - self.points[3]
        normal = get_unit_normal(hor, ver)
        distance = self.frame_shape[1] / 2 / np.tan(np.deg2rad(self.fov / 2))

        view = QMatrix4x4()
        view.setToIdentity()
        view.lookAt(QVector3D(*(center + normal * distance)), QVector3D(*center), QVector3D(*(ver)))

        return view

    def compute_wnd_mul_proj_matrix(self) -> QMatrix4x4:
        projection = QMatrix4x4()
        projection.setToIdentity()
        projection.perspective(self.fov, self.frame_shape[0] / self.frame_shape[1], 0.1, 100)

        window = QMatrix4x4()
        window.setToIdentity()
        res_width, res_height = get_proportional_scale_size(*self.frame_shape, *self.window_shape)
        window.scale(res_width / self.window_shape[0], res_height / self.window_shape[1])

        return window * projection
