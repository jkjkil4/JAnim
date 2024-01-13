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
from janim.utils.signal import Signal
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
            for item in info.origin.walk_self_and_descendants(info.decl_type)
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
        self._raise_error_if_no_points()
        return self.get()[0].copy()

    def get_end(self) -> np.ndarray:
        '''
        得到 ``points`` 的最后一个点 | Obtains the last point of ``points``.
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

    @Signal[[PointsFn]]
    @Component.as_able
    def apply_points_fn(
        as_data,
        func: PointsFn,
        *,
        about_point: Vect | None = None,
        about_edge: Vect = ORIGIN,
        self_only: bool = False
    ) -> Self:
        '''
        将所有点作为单独的一个参数传入 ``func``，并将 ``func`` 返回的结果作为新的点坐标数据

        视 ``about_point`` 为原点，若其为 ``None``，则将物件在 ``about_edge`` 方向上的边界作为 ``about_point``
        '''
        Cmpt_Points._raise_error_if_astype_and_self_only(as_data, self_only)

        info = Component.extract_as(as_data)

        if about_point is None:
            if self_only:
                # 前面的检查保证了 self_only==True 时，as_data 为 self 对象
                about_point = as_data.self_box.get(about_edge)
            else:
                about_point = Cmpt_Points.box.fget(as_data).get(about_edge)

        def apply(cmpt: Cmpt_Points):
            if not cmpt.has():
                return

            cmpt.set(func(cmpt.get() - about_point) + about_point)
            Cmpt_Points.apply_points_fn.emit(cmpt, func)

        if isinstance(as_data, Cmpt_Points):
            apply(as_data)

        if not self_only:
            for item in info.origin.walk_descendants(info.decl_type):
                cmpt = getattr(item, info.cmpt_name)
                apply(cmpt)

        return as_data

    @Component.as_able
    def apply_point_fn(
        as_data,
        func: PointFn,
        about_point: Vect | None = ORIGIN,
        **kwargs
    ) -> Self:
        '''
        对每个点依次传入 ``func`` 进行变换；以默认的原点作用变换，而不是物件的中心
        '''
        Cmpt_Points.apply_points_fn(
            as_data,
            lambda points: np.array([func(p) for p in points]),
            about_point=about_point,
            **kwargs
        )
        return as_data

    @Component.as_able
    def apply_matrix(
        as_data,
        matrix: VectArray,
        about_point: Vect | None = None,
        about_edge: Vect | None = None,
        **kwargs
    ) -> Self:
        '''
        将矩阵变换作用于 ``points``；以默认的原点作用变换，而不是物件的中心

        Apply a matrix transformation to the ``points``.
        Default to applying the transformation about the origin, not items center.
        '''
        matrix = np.array(matrix)
        if matrix.shape not in ((2, 2), (3, 3)):
            raise ValueError(f'只有 2x2 或 3x3 矩阵是有效的，而传入的是 {"x".join(matrix.shape)} 矩阵')

        if about_point is None and about_edge is None:
            about_point = ORIGIN

        # 使 2x2 和 3x3 矩阵都可用
        full_matrix = np.identity(3)
        full_matrix[:matrix.shape[0], :matrix.shape[1]] = matrix

        Cmpt_Points.apply_points_fn(
            as_data,
            lambda points: np.dot(points, full_matrix.T),
            about_point=about_point,
            about_edge=about_edge,
            **kwargs
        )

        return as_data

    @Component.as_able
    def apply_complex_fn(as_data, func: ComplexFn, **kwargs) -> Self:
        '''
        将复变函数作用于 ``points``；以默认的原点作用变换，而不是物件的中心

        Apply a complex-valued function to the ``points``.
        Default to applying the transformation about the origin, not items center.
        '''
        def R3_func(point):
            x, y, z = point
            xy_complex = func(complex(x, y))
            return [
                xy_complex.real,
                xy_complex.imag,
                z
            ]
        Cmpt_Points.apply_point_fn(as_data, R3_func, **kwargs)
        return as_data

    @Component.as_able
    def rotate(
        as_data,
        angle: float,
        *,
        axis: Vect = OUT,
        about_point: Vect | None = None,
        **kwargs
    ) -> Self:
        '''
        以 ``axis`` 为方向，``angle`` 为角度旋转，可传入 ``about_point`` 指定相对于以哪个点为中心

        Rotate the item by an ``angle`` around the specified ``axis``,
        with an optional ``about_point`` about which the rotation should be performed.
        '''
        rot_matrix_T = rotation_matrix(angle, axis).T
        Cmpt_Points.apply_points_fn(
            as_data,
            lambda points: np.dot(points, rot_matrix_T),
            about_point=about_point,
            **kwargs
        )
        return as_data

    @Component.as_able
    def flip(as_data, axis: Vect = UP, **kwargs) -> Self:
        '''
        绕 axis 轴翻转

        Flip the item around the specified axis.
        '''
        Cmpt_Points.rotate(as_data, PI, axis, **kwargs)
        return as_data

    @Component.as_able
    def scale(
        as_data,
        scale_factor: float | Iterable,
        *,
        min_scale_factor: float = 1e-8,
        **kwargs
    ) -> Self:
        '''
        将物件缩放指定倍数

        如果传入的倍数是可遍历的对象，那么则将其中的各个元素作为坐标各分量缩放的倍数，
        例如传入 ``scale_factor`` 为 ``(2, 0.5, 1)`` 则是在 ``x`` 方向上缩放为两倍，在 ``y`` 方向上压缩为原来的一半，在 ``z`` 方向上保持不变

        =====

        Scale the item by a specified factor.

        If the scale factor provided is an iterable object, each element
        will be used as the scaling factor for the corresponding coordinate component.

        For example, if ``scale_factor`` is ``(2, 0.5, 1)``, the item will be scaled by a factor
        of 2 along the ``x`` axis, compressed by half along the ``y`` axis, and remain unchanged along the ``z`` axis.
        '''
        if isinstance(scale_factor, Iterable):
            scale_factor = np.array(scale_factor).clip(min=min_scale_factor)
        else:
            scale_factor = max(scale_factor, min_scale_factor)

        Cmpt_Points.apply_points_fn(
            as_data,
            lambda points: scale_factor * points,
            **kwargs
        )
        return as_data

    @Component.as_able
    def stretch(as_data, factor: float, *, dim: int, **kwargs) -> Self:
        '''
        在指定的 ``dim`` 方向上使物件伸缩

        Stretch the object along the specified ``dim`` direction.
        '''
        def func(points):
            points[:, dim] *= factor
            return points
        Cmpt_Points.apply_points_fn(as_data, func, **kwargs)
        return as_data

    @Component.as_able
    def rescale_to_fit(
        as_data,
        length: float,
        dim: int,
        *,
        stretch: bool = False,
        self_only: bool = False,
        **kwargs
    ) -> Self:
        Cmpt_Points._raise_error_if_astype_and_self_only(as_data, self_only)

        if self_only:
            # 前面的检查保证了 self_only==True 时，as_data 为 self 对象
            old_length = as_data.self_box.length_over_dim(dim)
        else:
            old_length = Cmpt_Points.box.fget(as_data).length_over_dim(dim)

        if old_length == 0:
            return as_data

        if stretch:
            Cmpt_Points.stretch(
                as_data,
                length / old_length,
                dim,
                self_only=self_only,
                **kwargs
            )
        else:
            Cmpt_Points.scale(
                as_data,
                length / old_length,
                self_only=self_only,
                **kwargs
            )

        return as_data

    @Component.as_able
    def set_width(as_data, width: float, *, stretch: bool = False, **kwargs) -> Self:
        '''
        如果 ``stretch`` 为 ``False``（默认），则表示等比缩放

        If ``stretch`` is ``False`` (default), it indicates proportional scaling.
        '''
        return Cmpt_Points.rescale_to_fit(as_data, width, 0, stretch=stretch, **kwargs)

    @Component.as_able
    def set_height(as_data, height: float, *, stretch: bool = False, **kwargs) -> Self:
        '''
        如果 ``stretch`` 为 ``False``（默认），则表示等比缩放

        If ``stretch`` is ``False`` (default), it indicates proportional scaling.
        '''
        return Cmpt_Points.rescale_to_fit(as_data, height, 1, stretch=stretch, **kwargs)

    @Component.as_able
    def set_depth(as_data, depth: float, *, stretch: bool = False, **kwargs) -> Self:
        '''
        如果 ``stretch`` 为 ``False``（默认），则表示等比缩放

        If ``stretch`` is ``False`` (default), it indicates proportional scaling.
        '''
        return Cmpt_Points.rescale_to_fit(as_data, depth, 2, stretch=stretch, **kwargs)

    @Component.as_able
    def set_size(
        as_data,
        width: float | None = None,
        height: float | None = None,
        depth: float | None = None,
        **kwargs
    ) -> Self:
        if width:
            Cmpt_Points.set_width(as_data, width, True, **kwargs)
        if height:
            Cmpt_Points.set_height(as_data, height, True, **kwargs)
        if depth:
            Cmpt_Points.set_depth(as_data, depth, True, **kwargs)
        return as_data

    @Component.as_able
    def replace(
        as_data,
        item: Item,
        dim_to_match: int = 0,
        *,
        stretch: bool = False,
        self_only: bool = False,
        item_root_only: bool = False,
        **kwargs
    ) -> Self:
        '''
        放到 item 的位置，并且在 ``dim_to_match`` 维度上长度相同
        '''
        info = Component.extract_as(as_data)

        # 得到 item 的边界框
        if item_root_only:
            if not isinstance(item, info.decl_type):
                # TODO: i18n
                raise ValueError(f'传入了 item_root_only==True，但 {item.__class__.__name__} 不是支持的类型')

            item_box: Cmpt_Points.BoundingBox = getattr(item, info.cmpt_name).self_box

        else:
            cmpt = getattr(item.astype(info.decl_type), info.cmpt_name)
            all_points = cmpt.get_all()
            if len(all_points) == 0:
                return
            item_box = Cmpt_Points.BoundingBox(all_points)

        if stretch:
            # If stretch is True, rescale each dimension to match the corresponding dimension of the item.
            for i in range(3):
                Cmpt_Points.rescale_to_fit(
                    as_data,
                    item_box.length_over_dim(i),
                    i,
                    stretch=True,
                    self_only=self_only
                )
        else:
            # If stretch is False, rescale only the dimension specified by dim_to_match to match the item.
            Cmpt_Points.rescale_to_fit(
                as_data,
                item_box.length_over_dim(dim_to_match),
                dim_to_match,
                stretch=False,
                self_only=self_only,
                **kwargs
            )

        # Shift the object to the center of the specified item.
        Cmpt_Points.move_to(as_data, item_box.center(), self_only=self_only)

        return as_data

    @Component.as_able
    def surround(
        as_data,
        item: Item,
        dim_to_match: int = 0,
        *,
        stretch: bool = False,
        buff: float = MED_SMALL_BUFF,
        self_only: bool = False,
        **kwargs
    ) -> Self:
        '''
        与 ``replace`` 类似，但是会向外留出 ``buff`` 间距

        Similar to ``replace`` but leaves a buffer space of ``buff`` around the item.
        '''
        Cmpt_Points.replace(
            as_data,
            item,
            dim_to_match,
            stretch=stretch,
            self_only=self_only,
            **kwargs
        )

        box: Cmpt_Points.BoundingBox = Cmpt_Points.box.fget(as_data)
        length = box.length_over_dim(dim_to_match)

        Cmpt_Points.scale(as_data, (length + buff) / length, self_only=self_only)

        return as_data

    def put_start_and_end_on(self, start: Vect, end: Vect) -> Self:
        '''
        通过旋转和缩放，使得物件的起点和终点被置于 ``start`` 和 ``end``

        Rotate and scale this item such that its start and end points are positioned at ``start`` and ``end``.
        '''
        curr_start, curr_end = self.get_start(), self.get_end()
        curr_vect = curr_end - curr_start
        if np.all(curr_vect == 0):
            raise Exception("Cannot position endpoints of closed loop")
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

    @staticmethod
    def _raise_error_if_astype_and_self_only(as_data, self_only: bool) -> None:
        if not isinstance(as_data, Cmpt_Points) and self_only:
            name = inspect.currentframe().f_back.f_code.co_name
            # TODO: i18n
            raise ValueError(f'使用 astype 时，对 {name} 的调用不能传入 self_only=True')

    # endregion

    # region 位移 | movement

    @Component.as_able
    def shift(as_data, vector: Vect, **kwargs) -> Self:
        '''
        相对移动 ``vector`` 向量

        Shift the object by the specified ``vector``.
        '''
        Cmpt_Points.apply_points_fn(
            as_data,
            lambda points: points + vector,
            about_edge=None,
            **kwargs
        )
        return as_data

    @Component.as_able
    def move_to(
        self,
        target: Item | Vect,
        aligned_edge: Vect = ORIGIN,
        coor_mask: Iterable = (1, 1, 1)
    ) -> Self:
        '''
        移动到 ``target`` 的位置

        Move this item to the position of ``target``.
        '''
        if isinstance(target, Item):
            target = target.box.get(aligned_edge)
        point_to_align = self.box.get(aligned_edge)
        self.shift((target - point_to_align) * coor_mask)
        return self

    def align_to(
        self,
        item_or_point: Item | Vect,
        direction: Vect = ORIGIN
    ) -> Self:
        """
        Examples:
        item1.align_to(item2, UP) moves item1 vertically so that its
        top edge lines ups with item2's top edge.

        item1.align_to(item2, direction = RIGHT) moves item1
        horizontally so that it's center is directly above/below
        the center of item2
        """  # TODO: 完善 align_to 注释
        if isinstance(item_or_point, Item):
            point = item_or_point.box.get(direction)
        else:
            point = item_or_point

        for dim in range(3):
            if direction[dim] != 0:
                self.set_coord(point[dim], dim, direction)

        return self

    def to_center(self) -> Self:
        '''
        移动到原点 ``(0, 0, 0)``

        Move this item to the origin ``(0, 0, 0)``.
        '''
        self.shift(-self.box.center)
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
        buff: float = DEFAULT_ITEM_TO_ITEM_BUFF,
        aligned_edge: Vect = ORIGIN,
        coor_mask: Iterable = (1, 1, 1)
    ) -> Self:
        '''
        将该物件放到 ``target`` 旁边

        Position this item next to ``target``.
        '''
        if isinstance(target, Item):
            target = target.box.get(aligned_edge + direction)

        point_to_align = self.box.get(aligned_edge - direction)
        self.shift((target - point_to_align + buff * direction) * coor_mask)
        return self

    # TODO: shift_onto_screen

    def set_coord(self, value: float, dim: int, direction: Vect = ORIGIN) -> Self:
        curr = self.box.coord(dim, direction)
        shift_vect = np.zeros(3)
        shift_vect[dim] = value - curr
        self.shift(shift_vect)
        return self

    def set_x(self, x: float, direction: Vect = ORIGIN) -> Self:
        return self.set_coord(x, 0, direction)

    def set_y(self, y: float, direction: Vect = ORIGIN) -> Self:
        return self.set_coord(y, 1, direction)

    def set_z(self, z: float, direction: Vect = ORIGIN) -> Self:
        return self.set_coord(z, 2, direction)
