from __future__ import annotations

import inspect
from typing import Callable, Iterable, Self

import numpy as np

import janim.utils.refresh as refresh
from janim.components.component import Component
from janim.constants import (DEFAULT_ITEM_TO_ITEM_BUFF, DOWN, IN, LEFT,
                             MED_SMALL_BUFF, ORIGIN, OUT, PI, RIGHT, UP)
from janim.items.item import Item
from janim.typing import Vect, VectArray
from janim.utils.data import AlignedData
from janim.utils.signal import Signal
from janim.utils.bezier import interpolate
from janim.utils.space_ops import angle_of_vector, get_norm, rotation_matrix
from janim.utils.unique_nparray import UniqueNparray

type PointsFn = Callable[[np.ndarray], VectArray]
type PointFn = Callable[[np.ndarray], Vect]
type ComplexFn = Callable[[complex], complex]


class Cmpt_Points(Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._points = UniqueNparray()
        self.set([])

    def init_bind(self, bind: Component.BindInfo):
        super().init_bind(bind)

        item = bind.at_item

        item.__class__.children_changed.connect_refresh(item, self, Cmpt_Points.box.fget)

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy._points = UniqueNparray()
        cmpt_copy._points.data = self._points.data
        return cmpt_copy

    def __eq__(self, other: Cmpt_Points) -> bool:
        return id(self.get()) == id(other.get())

    @staticmethod
    def align_for_interpolate(cmpt1: Cmpt_Points, cmpt2: Cmpt_Points):
        len1, len2 = len(cmpt1.get()), len(cmpt2.get())

        if len1 == len2:
            if cmpt1 == cmpt2:
                return AlignedData(cmpt1, cmpt1, cmpt1)
            # cmpt1 != cmpt2
            return AlignedData(cmpt1, cmpt2, Cmpt_Points())

        if len1 > len2:
            return AlignedData(cmpt1, cmpt2.copy().resize(len1), Cmpt_Points())

        # len1 < len2
        return AlignedData(cmpt1.copy().resize(len2), cmpt2, Cmpt_Points())

    def interpolate(self, cmpt1: Cmpt_Points, cmpt2: Cmpt_Points, alpha: float) -> None:
        if cmpt1 == cmpt2:
            return

        self.set(interpolate(cmpt1.get(), cmpt2.get(), alpha))

    # region 点数据 | Points

    def get(self) -> np.ndarray:
        '''
        得到点坐标数据
        '''
        return self._points.data

    def get_all(self) -> np.ndarray:
        '''
        得到自己以及后代物件的所有点坐标数据
        '''
        point_datas = [self.get()]

        if self.bind is not None:
            for item in self.bind.at_item.walk_descendants(self.bind.decl_cls):
                cmpt = getattr(item, self.bind.key)
                if not isinstance(cmpt, Cmpt_Points):
                    continue    # pragma: no cover

                point_datas.append(cmpt.get())

        return np.vstack(point_datas)

    @Signal
    def set(self, points: VectArray) -> Self:
        '''
        设置点坐标数据，每个坐标点都有三个分量

        使用形如 ``.set([[1.5, 3, 2], [2, 1.5, 0]])`` 的形式
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
        '''清除点'''
        self.set(np.zeros((0, 3)))
        return self

    def extend(self, points: VectArray) -> Self:
        '''
        追加点坐标数据，每个坐标点都有三个分量

        使用形如 ``.append([[1.5, 3, 2], [2, 1.5, 0]])`` 的形式
        '''
        self.set(np.vstack([
            self.get(),
            points
        ]))
        return self

    @Signal
    def reverse(self) -> Self:
        '''使点倒序'''
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
        '''
        点的数量
        '''
        return len(self.get())

    def has(self) -> bool:
        '''
        是否有点坐标数据
        '''
        return self.count() > 0

    def get_start(self) -> np.ndarray:
        '''
        得到 ``points`` 的第一个点
        '''
        self._raise_error_if_no_points()
        return self.get()[0].copy()

    def get_end(self) -> np.ndarray:
        '''
        得到 ``points`` 的最后一个点
        '''
        self._raise_error_if_no_points()
        return self.get()[-1].copy()

    def _raise_error_if_no_points(self) -> None:
        if not self.has():
            name = inspect.currentframe().f_back.f_code.co_name
            # TODO: i18n
            raise ValueError(f'Cannot call {name} with no points')

    # endregion

    # region 边界框 | Bounding box

    @property
    @set.self_refresh_with_recurse(recurse_up=True)
    @refresh.register
    def box(self) -> BoundingBox:
        '''
        表示物件（包括后代物件）的矩形包围框
        '''
        box_datas = []

        if self.has():
            box_datas.append(self.self_box.data)

        if self.bind is not None:
            for item in self.bind.at_item.walk_descendants(self.bind.decl_cls):
                cmpt = getattr(item, self.bind.key)
                if not isinstance(cmpt, Cmpt_Points) or not cmpt.has():
                    continue

                box_datas.append(cmpt.self_box.data)

        return self.BoundingBox(np.vstack(box_datas) if box_datas else [])

    @property
    @set.self_refresh()
    @refresh.register
    def self_box(self) -> BoundingBox:
        '''
        同 ``box``，但仅表示自己 ``points`` 的包围框，不考虑后代物件的
        '''
        return self.BoundingBox(self.get())

    class BoundingBox:
        '''
        边界框，``self.data`` 包含三个元素，分别为左下，中心，右上
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

        def get_x(self, direction=ORIGIN) -> float:
            return self.coord(0, direction)

        @property
        def x(self) -> float:
            return self.get_x()

        def get_y(self, direction=ORIGIN) -> float:
            return self.coord(1, direction)

        @property
        def y(self) -> float:
            return self.get_y()

        def get_z(self, direction=ORIGIN) -> float:
            return self.coord(2, direction)

        @property
        def z(self) -> float:
            return self.get_z()

    # endregion

    # region 变换 | Transform

    @Signal
    def apply_points_fn(
        self,
        func: PointsFn,
        *,
        about_point: Vect | None = None,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False
    ) -> Self:
        '''
        将所有点作为单独的一个参数传入 ``func``，并将 ``func`` 返回的结果作为新的点坐标数据

        视 ``about_point`` 为原点，若其为 ``None``，则将物件在 ``about_edge`` 方向上的边界作为 ``about_point``
        '''
        if about_point is None and about_edge is not None:
            if root_only:
                about_point = self.self_box.get(about_edge)
            else:
                about_point = self.box.get(about_edge)

        def apply(cmpt: Cmpt_Points):
            if not cmpt.has():
                return

            if about_point is None:
                cmpt.set(func(cmpt.get()))
            else:
                cmpt.set(func(cmpt.get() - about_point) + about_point)

            Cmpt_Points.apply_points_fn.emit(cmpt, func)

        apply(self)

        if not root_only and self.bind is not None:
            for item in self.bind.at_item.walk_descendants(self.bind.decl_cls):
                cmpt = getattr(item, self.bind.key)
                if not isinstance(cmpt, Cmpt_Points):
                    continue    # pragma: no cover

                apply(cmpt)

        return self

    def apply_point_fn(
        self,
        func: PointFn,
        *,
        about_point: Vect | None = ORIGIN,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False
    ) -> Self:
        '''
        对每个点依次传入 ``func`` 进行变换；以默认的原点作用变换，而不是物件的中心
        '''
        self.apply_points_fn(
            lambda points: np.array([func(p) for p in points]),
            about_point=about_point,
            about_edge=about_edge,
            root_only=root_only
        )
        return self

    def apply_matrix(
        self,
        matrix: VectArray,
        *,
        about_point: Vect | None = None,
        about_edge: Vect | None = None,
        root_only: bool = False
    ) -> Self:
        '''
        将矩阵变换作用于 ``points``；以默认的原点作用变换，而不是物件的中心
        '''
        matrix = np.array(matrix)
        if matrix.shape not in ((2, 2), (3, 3)):
            raise ValueError(
                '只有 2x2 或 3x3 矩阵是有效的，'
                f'而传入的是 {"x".join(str(v) for v in matrix.shape)} 矩阵'
            )

        if about_point is None and about_edge is None:
            about_point = ORIGIN

        # 使 2x2 和 3x3 矩阵都可用
        full_matrix = np.identity(3)
        full_matrix[:matrix.shape[0], :matrix.shape[1]] = matrix

        self.apply_points_fn(
            lambda points: np.dot(points, full_matrix.T),
            about_point=about_point,
            about_edge=about_edge,
            root_only=root_only
        )

        return self

    def apply_complex_fn(
        self,
        func: ComplexFn,
        *,
        about_point: Vect | None = ORIGIN,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False
    ) -> Self:
        '''
        将复变函数作用于 ``points``；以默认的原点作用变换，而不是物件的中心
        '''
        def R3_func(point):
            x, y, z = point
            xy_complex = func(complex(x, y))
            return [
                xy_complex.real,
                xy_complex.imag,
                z
            ]
        self.apply_point_fn(
            R3_func,
            about_point=about_point,
            about_edge=about_edge,
            root_only=root_only
        )
        return self

    def rotate(
        self,
        angle: float,
        *,
        axis: Vect = OUT,
        about_point: Vect | None = None,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False
    ) -> Self:
        '''
        以 ``axis`` 为方向，``angle`` 为角度旋转，可传入 ``about_point`` 指定相对于以哪个点为中心
        '''
        rot_matrix_T = rotation_matrix(angle, axis).T
        self.apply_points_fn(
            lambda points: np.dot(points, rot_matrix_T),
            about_point=about_point,
            about_edge=about_edge,
            root_only=root_only
        )
        return self

    def flip(
        self,
        *,
        axis: Vect = UP,
        about_point: Vect | None = None,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False
    ) -> Self:
        '''
        绕 axis 轴翻转
        '''
        self.rotate(
            PI,
            axis=axis,
            about_point=about_point,
            about_edge=about_edge,
            root_only=root_only
        )
        return self

    def scale(
        self,
        scale_factor: float | Iterable,
        *,
        min_scale_factor: float = 1e-8,
        about_point: Vect | None = None,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False
    ) -> Self:
        '''
        将物件缩放指定倍数

        如果传入的倍数是可遍历的对象，那么则将其中的各个元素作为坐标各分量缩放的倍数，
        例如传入 ``scale_factor`` 为 ``(2, 0.5, 1)`` 则是在 ``x`` 方向上缩放为两倍，在 ``y`` 方向上压缩为原来的一半，在 ``z`` 方向上保持不变
        '''
        if isinstance(scale_factor, Iterable):
            scale_factor = np.array(scale_factor).clip(min=min_scale_factor)
        else:
            scale_factor = max(scale_factor, min_scale_factor)

        self.apply_points_fn(
            lambda points: scale_factor * points,
            about_point=about_point,
            about_edge=about_edge,
            root_only=root_only
        )
        return self

    def stretch(
        self,
        factor: float,
        *,
        dim: int,
        min_scale_factor: float = 1e-8,
        about_point: Vect | None = None,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False
    ) -> Self:
        '''
        在指定的 ``dim`` 方向上使物件伸缩
        '''
        factor = max(factor, min_scale_factor)

        def func(points):
            points[:, dim] *= factor
            return points

        self.apply_points_fn(
            func,
            about_point=about_point,
            about_edge=about_edge,
            root_only=root_only
        )
        return self

    def rescale_to_fit(
        self,
        length: float,
        *,
        dim: int,
        stretch: bool = False,
        min_scale_factor: float = 1e-8,
        about_point: Vect | None = None,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False
    ) -> Self:
        if root_only:
            old_length = self.self_box.length_over_dim(dim)
        else:
            old_length = self.box.length_over_dim(dim)

        if old_length == 0:
            return self

        if stretch:
            self.stretch(
                length / old_length,
                dim=dim,
                min_scale_factor=min_scale_factor,
                about_point=about_point,
                about_edge=about_edge,
                root_only=root_only,
            )
        else:
            self.scale(
                length / old_length,
                min_scale_factor=min_scale_factor,
                about_point=about_point,
                about_edge=about_edge,
                root_only=root_only
            )

        return self

    def set_width(self, width: float, *, stretch: bool = False, **kwargs) -> Self:
        '''
        如果 ``stretch`` 为 ``False`` （默认），则表示等比缩放
        '''
        return self.rescale_to_fit(width, dim=0, stretch=stretch, **kwargs)

    def set_height(self, height: float, *, stretch: bool = False, **kwargs) -> Self:
        '''
        如果 ``stretch`` 为 ``False`` （默认），则表示等比缩放
        '''
        return self.rescale_to_fit(height, dim=1, stretch=stretch, **kwargs)

    def set_depth(self, depth: float, *, stretch: bool = False, **kwargs) -> Self:
        '''
        如果 ``stretch`` 为 ``False`` （默认），则表示等比缩放
        '''
        return self.rescale_to_fit(depth, dim=2, stretch=stretch, **kwargs)

    def set_size(
        self,
        width: float | None = None,
        height: float | None = None,
        depth: float | None = None,
        **kwargs
    ) -> Self:
        if width:
            self.set_width(width, stretch=True, **kwargs)
        if height:
            self.set_height(height, stretch=True, **kwargs)
        if depth:
            self.set_depth(depth, stretch=True, **kwargs)
        return self

    def replace(
        self,
        item: Item,
        dim_to_match: int = 0,
        *,
        stretch: bool = False,
        root_only: bool = False,
        item_root_only: bool = False
    ) -> Self:
        '''
        放到 item 的位置，并且在 ``dim_to_match`` 维度上长度相同
        '''
        cmpt = self.get_same_cmpt(item)
        item_box = cmpt.self_box if item_root_only else cmpt.box

        if stretch:
            # If stretch is True, rescale each dimension to match the corresponding dimension of the item.
            for i in range(3):
                self.rescale_to_fit(
                    item_box.length_over_dim(i),
                    dim=i,
                    stretch=True,
                    root_only=root_only
                )
        else:
            # If stretch is False, rescale only the dimension specified by dim_to_match to match the item.
            self.rescale_to_fit(
                item_box.length_over_dim(dim_to_match),
                dim=dim_to_match,
                stretch=False,
                root_only=root_only
            )

        # Shift the object to the center of the specified item.
        self.move_to(item_box.center, root_only=root_only)

        return self

    def surround(
        self,
        item: Item,
        dim_to_match: int = 0,
        *,
        stretch: bool = False,
        buff: float = MED_SMALL_BUFF,
        root_only: bool = False,
        item_root_only: bool = False
    ) -> Self:
        '''
        与 ``replace`` 类似，但是会向外留出 ``buff`` 间距
        '''
        self.replace(
            item,
            dim_to_match,
            stretch=stretch,
            root_only=root_only,
            item_root_only=item_root_only
        )

        box = self.self_box if root_only else self.box

        if stretch:
            for i in range(3):
                length = box.length_over_dim(i)
                if length == 0:
                    continue
                self.stretch((length + buff * 2) / length, dim=i, root_only=root_only)
        else:
            length = box.length_over_dim(dim_to_match)
            self.scale((length + buff * 2) / length, root_only=root_only)

        return self

    def put_start_and_end_on(self, start: Vect, end: Vect) -> Self:
        '''
        通过旋转和缩放，使得物件的起点和终点被置于 ``start`` 和 ``end``
        '''
        curr_start, curr_end = self.get_start(), self.get_end()
        curr_vect = curr_end - curr_start
        if np.all(curr_vect == 0):
            raise ValueError("Cannot position endpoints of closed loop")
        target_vect = end - start
        self.scale(
            get_norm(target_vect) / get_norm(curr_vect),
            about_point=curr_start,
        )
        self.rotate(
            angle_of_vector(target_vect) - angle_of_vector(curr_vect),
        )
        self.rotate(
            np.arctan2(curr_vect[2], get_norm(curr_vect[:2])) - np.arctan2(target_vect[2], get_norm(target_vect[:2])),
            axis=np.array([-target_vect[1], target_vect[0], 0]),
        )
        self.shift(start - self.get_start())
        return self

    # endregion

    # region 位移 | movement

    def shift(self, vector: Vect, *, root_only=False) -> Self:
        '''
        相对移动 ``vector`` 向量
        '''
        self.apply_points_fn(
            lambda points: points + vector,
            about_edge=None,
            root_only=root_only
        )
        return self

    def move_to(
        self,
        target: Item | Vect,
        *,
        aligned_edge: Vect = ORIGIN,
        coor_mask: Iterable = (1, 1, 1),
        root_only: bool = False,
        item_root_only: bool = False
    ) -> Self:
        '''
        移动到 ``target`` 的位置
        '''
        if isinstance(target, Item):
            cmpt = self.get_same_cmpt(target)
            box = cmpt.self_box if item_root_only else cmpt.box
            target = box.get(aligned_edge)

        point_to_align = self.box.get(aligned_edge)
        self.shift((target - point_to_align) * coor_mask, root_only=root_only)

        return self

    # TODO: def align_to(
    #     self,
    #     item_or_point: Item | Vect,
    #     direction: Vect = ORIGIN
    # ) -> Self:
    #     """
    #     Examples:
    #     item1.align_to(item2, UP) moves item1 vertically so that its
    #     top edge lines ups with item2's top edge.

    #     item1.align_to(item2, direction = RIGHT) moves item1
    #     horizontally so that it's center is directly above/below
    #     the center of item2
    #     """  # TODO: 完善 align_to 注释
    #     if isinstance(item_or_point, Item):
    #         point = item_or_point.box.get(direction)
    #     else:
    #         point = item_or_point

    #     for dim in range(3):
    #         if direction[dim] != 0:
    #             self.set_coord(point[dim], dim, direction)

    #     return self

    def to_center(self, root_only=False) -> Self:
        '''
        移动到原点 ``(0, 0, 0)``
        '''
        self.shift(-self.box.center, root_only=root_only)
        return self

    # TODO: def to_border(
    #     self,
    #     direction: Vect,
    #     buff: float = DEFAULT_ITEM_TO_EDGE_BUFF
    # ) -> Self:
    #     """
    #     Direction just needs to be a vector pointing towards side or
    #     corner in the 2d plane.
    #     """
    #     target_point = np.sign(direction) * (FRAME_X_RADIUS, FRAME_Y_RADIUS, 0)
    #     point_to_align = self.box.get(direction)
    #     shift_val = target_point - point_to_align - buff * np.array(direction)
    #     shift_val = shift_val * abs(np.sign(direction))
    #     self.shift(shift_val)
    #     return self

    def next_to(
        self,
        target: Item | Vect,
        direction: Vect = RIGHT,
        *,
        buff: float = DEFAULT_ITEM_TO_ITEM_BUFF,
        aligned_edge: Vect = ORIGIN,
        coor_mask: Iterable = (1, 1, 1),
        root_only: bool = False,
        item_root_only: bool = False
    ) -> Self:
        '''
        将该物件放到 ``target`` 旁边
        '''
        if isinstance(target, Item):
            cmpt = self.get_same_cmpt(target)
            box = cmpt.self_box if item_root_only else cmpt.box
            target = box.get(aligned_edge + direction)

        point_to_align = self.box.get(aligned_edge - direction)
        self.shift(
            (target - point_to_align + buff * direction) * coor_mask,
            root_only=root_only
        )
        return self

    # TODO: shift_onto_screen

    def set_coord(self, value: float, *, dim: int, direction: Vect = ORIGIN, root_only=False) -> Self:
        curr = self.box.coord(dim, direction)
        shift_vect = np.zeros(3)
        shift_vect[dim] = value - curr
        self.shift(shift_vect, root_only=root_only)
        return self

    def set_x(self, x: float, direction: Vect = ORIGIN) -> Self:
        return self.set_coord(x, dim=0, direction=direction)

    def set_y(self, y: float, direction: Vect = ORIGIN) -> Self:
        return self.set_coord(y, dim=1, direction=direction)

    def set_z(self, z: float, direction: Vect = ORIGIN) -> Self:
        return self.set_coord(z, dim=2, direction=direction)
