from __future__ import annotations
import itertools as it

from PySide6.QtGui import QMatrix4x4, QVector3D

from janim.constants import *
from janim.items.item import Item, MethodGroup
from janim.utils.math_functions import (
    get_unit_normal, get_norm, 
    get_proportional_scale_size
)
from janim.shaders.render import RenderData

class Scene:
    anti_alias_width = 0.015

    def __init__(self) -> None:
        self.camera = Camera()

        # relation
        self.items: list[Item] = []

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
    
    def get_family(self) -> list[Item]:
        return list(it.chain(*(item.get_family() for item in self.items)))
    
    #endregion

    #region 渲染

    def render(self) -> None:
        camera_scale_factor = self.camera.get_vertical_dist() / self.camera.frame_shape[1]

        data = RenderData(
            self.anti_alias_width,
            self.camera.wnd_shape,
            self.camera.compute_view_matrix(),
            self.camera.compute_wnd_mul_proj_matrix()
        )

        for item in self:
            item.render(data)
    
    #endregion

class Camera(Item):
    frame_shape = (FRAME_WIDTH, FRAME_HEIGHT)
    wnd_shape = (1920, 1080)
    center_point = ORIGIN

    def __init__(self) -> None:
        super().__init__()

        self.reset()
    
    def reset(self):
        self.fov = 45
        self.set_points([ORIGIN, LEFT_SIDE, RIGHT_SIDE, BOTTOM, TOP])
        return self

    def get_horizontal_vect(self) -> np.ndarray:
        return self.points[2] - self.points[1]

    def get_horizontal_dist(self) -> float:
        return get_norm(self.get_horizontal_vect())
    
    def get_vertical_vect(self) -> np.ndarray:
        return self.points[4] - self.points[3]
    
    def get_vertical_dist(self) -> float:
        return get_norm(self.get_vertical_vect())

    def compute_view_matrix(self) -> QMatrix4x4:
        center = self.points[0]
        hor = self.get_horizontal_vect()
        ver = self.get_vertical_vect()
        normal = get_unit_normal(hor, ver)
        distance = get_norm(ver) / 2 / np.tan(np.deg2rad(self.fov / 2))

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
        res_width, res_height = get_proportional_scale_size(*self.frame_shape, *self.wnd_shape)
        window.scale(res_width / self.wnd_shape[0], res_height / self.wnd_shape[1])

        return window * projection
