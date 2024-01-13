from __future__ import annotations

import inspect
from typing import Self

import numpy as np

import janim.utils.refresh as refresh
from janim.components.component import Component
from janim.constants import DOWN, IN, LEFT, ORIGIN, OUT, RIGHT, UP
from janim.typing import Vect, VectArray
from janim.utils.signal import Signal
from janim.utils.unique_nparray import UniqueNparray


class Cmpt_Points(Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._points = UniqueNparray()
        self.set([])

    def init_bind(self, bind_info: Component.BindInfo):
        super().init_bind(bind_info)

        item = bind_info.at_item

        item.__class__.children_changed.connect_refresh(item, self, Cmpt_Points.box.fget)

    # region 点数据 | Points

    def get(self) -> np.ndarray:
        '''
        得到点坐标数据
        '''
        return self._points.data

    @Component.as_able
    def get_all(as_data) -> np.ndarray:
        '''
        得到自己以及后代物件的所有点坐标数据
        '''
        info = Component.extract_as(as_data)

        return np.vstack([
            getattr(item, info.cmpt_name).get()
            for item in info.origin.walk_self_and_descendants(info.as_type)
        ])

    @Signal
    def set(self, points: VectArray) -> Self:
        '''
        设置点坐标数据，每个坐标点都有三个分量

        使用形如 ``.set([[1.5, 3, 2], [2, 1.5, 0]])`` 的形式

        Set point coordinate data, with each point having three components.

        Use a format like ``.set([[1.5, 3, 2], [2, 1.5, 0]])``.
        '''
        if not isinstance(points, np.ndarray):
            points = np.array(points)
        if points.size == 0:
            points = np.zeros((0, 3))

        assert points.ndim == 2
        assert points.shape[1] == 3

        cnt_changed = len(points) != len(self._points.data)

        self._points.data = points

        if cnt_changed:
            Cmpt_Points.set.emit(self, key='count')
        Cmpt_Points.set.emit(self)

        return self

    def clear(self) -> Self:
        '''清除点 | clear points'''
        self.set(np.zeros((0, 3)))
        return self

    def append(self, points: VectArray) -> Self:
        '''
        追加点坐标数据，每个坐标点都有三个分量

        使用形如 ``.append([[1.5, 3, 2], [2, 1.5, 0]])`` 的形式

        Append point coordinate data, with each point having three components.

        Use a format like ``.append([[1.5, 3, 2], [2, 1.5, 0]])``.
        '''
        self.set(np.vstack([
            self.get(),
            points
        ]))
        return self

    @Signal
    def reverse(self) -> Self:
        '''使点倒序 | reverse the order of points'''
        self.set(self.get()[::-1])
        Cmpt_Points.reverse.emit(self)
        return self

    def resize(self, size: int) -> Self:
        # TODO: resize 注释
        points = self.get()
        if size < len(points):
            self.set(points[:size])

        elif size > len(points):
            if len(points) == 0:
                self.set(np.zeros((size, 3)))
            else:
                self.set(np.vstack([
                    points,
                    np.repeat([points[-1]], size - len(points), axis=0)
                ]))

        return self

    def count(self) -> int:
        return len(self.get())

    def has(self) -> bool:
        return self.count() > 0

    def get_start(self) -> np.ndarray:
        '''
        得到 ``points`` 的第一个点 | Obtains the first point of ``points``.
        '''
        self._throw_error_if_no_points()
        return self.get()[0].copy()

    def get_end(self) -> np.ndarray:
        '''
        得到 ``points`` 的最后一个点 | Obtains the last point of ``points``.
        '''
        self._throw_error_if_no_points()
        return self.get()[-1].copy()

    def _throw_error_if_no_points(self) -> None:
        if not self.has():
            name = inspect.currentframe().f_back.f_code.co_name
            raise ValueError(f'Cannot call {name} with no points')

    # endregion

    # region 边界框 | Bounding box

    @set.self_refresh_with_recurse(recurse_up=True)
    @refresh.register
    def _box(self) -> BoundingBox:
        return self.BoundingBox(self.get_all())

    @property
    @Component.as_able
    def box(as_data) -> BoundingBox:
        '''
        表示物件（包括后代物件）的矩形包围框

        Rectangular bounding box of the item (including descendant-items).
        '''
        if isinstance(as_data, Cmpt_Points):
            return as_data._box()

        return Cmpt_Points.BoundingBox(
            Cmpt_Points.get_all(as_data)
        )

    @property
    @set.self_refresh()
    @refresh.register
    def self_box(self) -> BoundingBox:
        '''
        同 ``box``，但仅表示自己 ``points`` 的包围框，不考虑后代物件的

        Same as ``box``, but only represents the bounding box of its own ``points``, excluding descendant-items.
        '''
        return self.BoundingBox(self.get())

    class BoundingBox:
        '''
        边界框，``self.data`` 包含三个元素，分别为左下，中心，右上

        Bounding box, ``self.data`` includes three elements representing the bottom-left, center, and top-right.
        '''
        def __init__(self, points: VectArray):
            self.data = self.compute(points)

        @staticmethod
        def compute(points: VectArray) -> np.ndarray:
            '''
            根据传入的 ``points`` 计算得到包围框的 左下、中心、右上 三个点
            '''
            points = np.array(points)

            if len(points) == 0:
                return np.zeros((3, 3))

            mins = points.min(0)
            maxs = points.max(0)
            mids = (mins + maxs) / 2

            return np.array([mins, mids, maxs])

        def get(self, direction: Vect) -> np.ndarray:
            '''
            获取边界框边上的坐标

            例如：

            - 传入 UR，则返回边界框右上角的坐标
            - 传入 RIGHT，则返回边界框右侧中心的坐标

            =====

            Obtains the coordinates on the borders of the bounding box.

            Examples:

            - If UR is passed, it returns the coordinates of the upper-right corner of the bounding box.
            - If RIGHT is passed, it returns the coordinates of the center on the right side of the bounding box.
            '''
            indices = (np.sign(direction) + 1).astype(int)
            return np.array([
                self.data[indices[i]][i]
                for i in range(3)
            ])

        def get_continuous(self, direction: Vect) -> np.ndarray:
            '''
            得到从中心发出的方向为 ``direction`` 的射线与边界框的交点
            '''
            direction = np.array(direction)

            dl, center, ur = self.data
            corner_vect = (ur - center)

            return center + direction * np.min(
                np.abs(
                    np.true_divide(
                        corner_vect, direction,
                        out=np.full((3, ), np.inf),
                        where=(direction != 0)
                    )
                )
            )

        @property
        def top(self) -> np.ndarray:
            return self.get(UP)

        @property
        def bottom(self) -> np.ndarray:
            return self.get(DOWN)

        @property
        def right(self) -> np.ndarray:
            return self.get(RIGHT)

        @property
        def left(self) -> np.ndarray:
            return self.get(LEFT)

        @property
        def zenith(self) -> np.ndarray:
            return self.get(OUT)

        @property
        def nadir(self) -> np.ndarray:
            return self.get(IN)

        @property
        def center(self) -> np.ndarray:
            return self.data[1]

        def length_over_dim(self, dim: int) -> float:
            return abs((self.data[2] - self.data[0])[dim])

        @property
        def width(self) -> float:
            return self.length_over_dim(0)

        @property
        def height(self) -> float:
            return self.length_over_dim(1)

        @property
        def depth(self) -> float:
            return self.length_over_dim(2)

        def coord(self, dim: int, direction=ORIGIN) -> float:
            return self.get(direction)[dim]

        @property
        def x(self, direction=ORIGIN) -> float:
            return self.coord(0, direction)

        @property
        def y(self, direction=ORIGIN) -> float:
            return self.coord(1, direction)

        @property
        def z(self, direction=ORIGIN) -> float:
            return self.coord(2, direction)

    # endregion
