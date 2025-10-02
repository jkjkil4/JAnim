from __future__ import annotations

import inspect
import types
from typing import TYPE_CHECKING, Callable, Iterable, Self

import numpy as np

import janim.utils.refresh as refresh
from janim.anims.method_updater_meta import register_updater
from janim.components.component import Component
from janim.constants import (DEFAULT_ITEM_TO_EDGE_BUFF,
                             DEFAULT_ITEM_TO_ITEM_BUFF, DOWN, IN, LEFT,
                             MED_SMALL_BUFF, ORIGIN, OUT, PI, RIGHT, UP)
from janim.exception import InvaildMatrixError, PointError
from janim.items.item import Item
from janim.locale.i18n import get_local_strings
from janim.typing import Vect, VectArray
from janim.utils.bezier import integer_interpolate, interpolate
from janim.utils.config import Config
from janim.utils.data import AlignedData, Array
from janim.utils.iterables import resize_and_repeatedly_extend
from janim.utils.paths import PathFunc, straight_path
from janim.utils.signal import Signal
from janim.utils.simple_functions import clip
from janim.utils.space_ops import (angle_of_vector, get_norm, normalize,
                                   rotation_between_vectors, rotation_matrix)

if TYPE_CHECKING:
    from janim.camera.camera import Camera

_ = get_local_strings('points')

type PointsFn = Callable[[np.ndarray], VectArray]
type PointFn = Callable[[np.ndarray], Vect]
type ComplexFn = Callable[[complex], complex]

DEFAULT_POINTS_ARRAY = Array()
DEFAULT_POINTS_ARRAY.data = np.zeros((0, 3))


class Cmpt_Points[ItemT](Component[ItemT]):
    resize_func = staticmethod(resize_and_repeatedly_extend)
    ''''''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._points = DEFAULT_POINTS_ARRAY.copy()

    def init_bind(self, bind: Component.BindInfo):
        super().init_bind(bind)

        item = bind.at_item

        item.__class__.children_changed.connect_refresh(item, self, Cmpt_Points.box.fget)

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy._points = self._points.copy()
        return cmpt_copy

    def become(self, other: Cmpt_Points) -> Self:
        if not self._points.is_share(other._points):
            self._points = other._points.copy()
            Cmpt_Points.set.emit(self)
        return self

    def not_changed(self, other: Cmpt_Points) -> bool:
        return self._points.is_share(other._points)

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_Points, cmpt2: Cmpt_Points) -> AlignedData[Self]:
        len1, len2 = len(cmpt1.get()), len(cmpt2.get())

        cmpt1_copy = cmpt1.copy()
        cmpt2_copy = cmpt2.copy()

        if len1 < len2:
            cmpt1_copy.resize(len2)
        elif len1 > len2:
            cmpt2_copy.resize(len1)

        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

    def interpolate(
        self,
        cmpt1: Self,
        cmpt2: Self,
        alpha: float,
        *,
        path_func: PathFunc = straight_path
    ) -> None:
        if not cmpt1._points.is_share(cmpt2._points) or not cmpt1._points.is_share(self._points):
            if cmpt1._points.is_share(cmpt2._points):
                self._points = cmpt1._points.copy()
            else:
                self.set(path_func(cmpt1.get(), cmpt2.get(), alpha))

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
        point_datas = [
            cmpt.get()
            for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock()
        ]
        return np.vstack(point_datas)

    @Signal
    def set(self, points: VectArray) -> Self:
        '''
        设置点坐标数据，每个坐标点都有三个分量

        使用形如 ``.set([[1.5, 3, 2], [2, 1.5, 0]])`` 的形式
        '''
        points = np.asarray(points)
        if points.size == 0:
            points = np.zeros((0, 3))

        assert points.ndim == 2
        assert points.shape[1] == 3

        cnt_changed = len(points) != self._points.len()

        self._points.data = points

        if cnt_changed:
            Cmpt_Points.set.emit(self, key='count')
        Cmpt_Points.set.emit(self)

        return self

    def clear(self) -> Self:
        '''清除点'''
        self.set(DEFAULT_POINTS_ARRAY.data)
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

    def resize(self, length: int) -> Self:
        self.set(self.resize_func(self.get(), length))
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
        return self._points.data[0]

    def get_end(self) -> np.ndarray:
        '''
        得到 ``points`` 的最后一个点
        '''
        self._raise_error_if_no_points()
        return self._points.data[-1]

    def get_start_and_end(self) -> tuple[np.ndarray, np.ndarray]:
        '''
        得到 ``points`` 的第一个和最后一个点
        '''
        return (self.get_start(), self.get_end())

    def point_from_proportion(self, alpha: float) -> np.ndarray:
        points = self._points.data
        i, subalpha = integer_interpolate(0, len(points) - 1, alpha)
        return interpolate(points[i], points[i + 1], subalpha)

    def pfp(self, alpha) -> np.ndarray:
        '''``point_from_proportion`` 的缩写'''
        return self.point_from_proportion(alpha)

    def _raise_error_if_no_points(self) -> None:
        if not self.has():
            name = inspect.currentframe().f_back.f_code.co_name
            raise PointError(_('Cannot call {name} with no points').format(name=name))

    # endregion

    # region 边界框 | Bounding box

    @property
    @set.self_refresh_with_recurse(recurse_up=True)
    @refresh.register
    def box(self) -> BoundingBox:
        '''
        表示物件（包括后代物件）的矩形包围框
        '''
        box_datas = [
            cmpt.self_box.data
            for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock()
            if cmpt.has()
        ]
        return self.BoundingBox(np.vstack(box_datas) if box_datas else [])

    @property
    @set.self_refresh
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
            points = np.asarray(points)

            if len(points) == 0:
                return np.zeros((3, 3))

            mins = np.nanmin(points, axis=0)
            maxs = np.nanmax(points, axis=0)
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

        def get_corners(self) -> np.ndarray:
            '''得到包围框（立方体）的八个顶点'''
            x1, y1, z1 = self.data[0]
            x2, y2, z2 = self.data[2]

            # 不直接使用 `self.get` 是因为它太慢了
            return np.array([
                [x1, y1, z1],
                [x1, y1, z2],
                [x1, y2, z1],
                [x1, y2, z2],
                [x2, y1, z1],
                [x2, y1, z2],
                [x2, y2, z1],
                [x2, y2, z2],
            ])

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

        for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
            if cmpt.has():
                if about_point is None:
                    cmpt.set(func(cmpt.get()))
                else:
                    cmpt.set(func(cmpt.get() - about_point) + about_point)

            Cmpt_Points.apply_points_fn.emit(cmpt, func, about_point)

        return self

    def apply_point_fn(
        self,
        func: PointFn,
        *,
        about_point: Vect | None = ORIGIN,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False,
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
        root_only: bool = False,
    ) -> Self:
        '''
        将矩阵变换作用于 ``points``；以默认的原点作用变换，而不是物件的中心
        '''
        matrix = np.array(matrix)
        if matrix.shape not in ((2, 2), (3, 3)):
            raise InvaildMatrixError(
                _('Only 2x2 or 3x3 matrix are valid, but a {shape} matrix was passed in')
                .format(shape="x".join(str(v) for v in matrix.shape))
            )

        if about_point is None and about_edge is None:
            about_point = ORIGIN

        # 使 2x2 和 3x3 矩阵都可用
        full_matrix = np.identity(3)
        full_matrix[:matrix.shape[0], :matrix.shape[1]] = matrix

        self.apply_points_fn(
            lambda points: points @ full_matrix.T,
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
        root_only: bool = False,
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

    @register_updater(
        lambda self, p, angle, **kwargs:
            self.rotate(angle * p.alpha, **kwargs),
        grouply=True
    )
    def rotate(
        self,
        angle: float,
        *,
        axis: Vect = OUT,
        about_point: Vect | None = None,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False,
    ) -> Self:
        '''
        以 ``axis`` 为方向，``angle`` 为角度旋转，可传入 ``about_point`` 指定相对于以哪个点为中心
        '''
        rot_matrix_T = rotation_matrix(angle, axis).T
        self.apply_points_fn(
            lambda points: points @ rot_matrix_T,
            about_point=about_point,
            about_edge=about_edge,
            root_only=root_only
        )
        return self

    def flip(
        self,
        axis: Vect = UP,
        *,
        about_point: Vect | None = None,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False,
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

    @register_updater(
        lambda self, p, scale_factor, **kwargs:
            self.scale((np.asarray(scale_factor) - 1) * p.alpha + 1, **kwargs),
        grouply=True
    )
    def scale(
        self,
        scale_factor: float | Iterable,
        *,
        min_scale_factor: float = 1e-8,
        about_point: Vect | None = None,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False,
    ) -> Self:
        '''
        将物件缩放指定倍数

        如果传入的倍数是可遍历的对象，那么则将其中的各个元素作为坐标各分量缩放的倍数，
        例如传入 ``scale_factor`` 为 ``(2, 0.5, 1)`` 则是在 ``x`` 方向上缩放为两倍，在 ``y`` 方向上压缩为原来的一半，在 ``z`` 方向上保持不变
        '''
        if isinstance(scale_factor, Iterable):
            sgn = np.sign(scale_factor)
            scale_factor = sgn * abs(np.asarray(scale_factor)).clip(min=min_scale_factor)
        else:
            if scale_factor >= 0:
                scale_factor = max(scale_factor, min_scale_factor)
            else:
                scale_factor = min(scale_factor, -min_scale_factor)

        self.apply_points_fn(
            lambda points: scale_factor * points,
            about_point=about_point,
            about_edge=about_edge,
            root_only=root_only
        )
        return self

    @register_updater(
        lambda self, p, factor, **kwargs:
            self.stretch((factor - 1) * p.alpha + 1, **kwargs),
        grouply=True
    )
    def stretch(
        self,
        factor: float,
        *,
        dim: int,
        min_scale_factor: float = 1e-8,
        about_point: Vect | None = None,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False,
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
        root_only: bool = False,
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
        if width is not None:
            self.set_width(width, stretch=True, **kwargs)
        if height is not None:
            self.set_height(height, stretch=True, **kwargs)
        if depth is not None:
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
        item_root_only: bool = False,
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

    @register_updater(
        lambda self, p, factor=0.2, direction=RIGHT, **kwargs:
            self.shear(factor * p.alpha, direction, **kwargs),
        grouply=True
    )
    def shear(
        self,
        factor: float = 0.2,
        direction: Vect = RIGHT,
        *,
        about_point: Vect | None = None,
        about_edge: Vect = ORIGIN,
        root_only: bool = False
    ) -> Self:
        '''
        切变

        - ``factor`` 表示切变的程度
        - ``direction`` 表示切变的方向
        - 可以传入 ``about_point`` 或 ``about_edge`` 控制参考点
        '''
        mat_shear = [
            [1, factor, 0],
            [0, 1, 0],
            [0, 0, 1]
        ]
        if np.isclose(normalize(direction), RIGHT).all():
            mat = mat_shear
        else:
            mat_rot = rotation_between_vectors(direction, RIGHT)
            # mat_rot.T == mat_rot.I
            mat = mat_rot.T @ mat_shear @ mat_rot

        self.apply_matrix(mat, about_point=about_point, about_edge=about_edge, root_only=root_only)
        return self

    def put_start_and_end_on(self, start: Vect, end: Vect) -> Self:
        '''
        通过旋转和缩放，使得物件的起点和终点被置于 ``start`` 和 ``end``
        '''
        start, end = np.asarray(start), np.asarray(end)

        curr_start, curr_end = self.get_start(), self.get_end()
        curr_vect = curr_end - curr_start
        if np.all(curr_vect == 0):
            raise PointError(_('Cannot position endpoints of closed loop'))
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

    @property
    @set.self_refresh
    @refresh.register
    def unit_normal(self) -> np.ndarray:
        '''
        计算三维点集的拟合平面的单位法向量
        '''
        points = self.get()

        # 质心
        centroid = np.mean(points, axis=0)

        # 协方差矩阵
        A = points - centroid
        C = A.T @ A

        # 求特征值和特征向量，最小特征值对应的特征向量就是法向量
        eigvals, eigvecs = np.linalg.eigh(C)
        normal = eigvecs[:, np.argmin(eigvals)]
        return normalize(normal)

    def face_to_camera(
        self,
        camera: Camera | types.EllipsisType = ...,
        *,
        rotate: float = 0,
        inverse: bool = False,
        normal_vector: Vect | types.EllipsisType = ...,
        about_point: Vect | None = None,
        about_edge: Vect | None = ORIGIN,
        root_only: bool = False,
    ) -> Self:
        '''
        使物件面向摄像机

        实用参数：

        - ``rotate``：在面向摄像机的基础上，绕摄像机视角旋转的角度

        - ``inverse``：是否让物件背向摄像机

        - 视 ``about_point`` 为参考点，若其为 ``None``，则将物件在 ``about_edge`` 方向上的边界作为 ``about_point``

        可手动指定 ``camera`` 和法向量 ``normal_vector``，若无则会自动获取：

        - ``camera`` 默认为时间轴的 ``self.camera``

        - ``normal_vector`` 默认通过 :meth:`unit_normal` 计算
        '''
        if camera is ...:
            from janim.anims.timeline import Timeline
            camera = Timeline.get_context().camera.current()

        if normal_vector is ...:
            vectors = [
                cmpt.unit_normal
                for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only)
                if cmpt.has()
            ]
            normal_vector = np.sum(vectors, axis=0)
            if np.allclose(normal_vector, 0):
                normal_vector = normalize(vectors[0])
            else:
                normal_vector = normalize(normal_vector)

        if inverse:
            normal_vector = -normal_vector

        info = camera.points.info
        camera_axis = info.camera_location - info.center
        camera_transform = rotation_between_vectors(normal_vector, camera_axis)

        up = np.cross(normal_vector, RIGHT)
        if inverse:
            up = -up
        mapped_up = up @ camera_transform.T

        rot_transform = rotation_between_vectors(mapped_up, info.vertical_vect)
        if rotate != 0:
            rot_transform @= rotation_matrix(rotate, camera_axis)

        self.apply_matrix(
            rot_transform @ camera_transform,
            about_point=about_point,
            about_edge=about_edge,
            root_only=root_only
        )
        return self

    # endregion

    # region 位移 | movement

    @register_updater(
        lambda self, p, vector, *, root_only=False:
            self.shift(np.asarray(vector) * p.alpha, root_only=root_only)
    )
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

    @staticmethod
    def _compute_move_shift(
        src: Cmpt_Points,
        target: Item | Vect,
        aligned_edge: Vect,
        coor_mask: Iterable,
        root_only: bool = False,
        item_root_only: bool = False
    ) -> np.ndarray:
        if isinstance(target, Item):
            cmpt = src.get_same_cmpt(target)
            box = cmpt.self_box if item_root_only else cmpt.box
            target = box.get(aligned_edge)

        point_to_align = (src.self_box if root_only else src.box).get(aligned_edge)
        return (target - point_to_align) * coor_mask

    def move_to(
        self,
        target: Item | Vect,
        *,
        aligned_edge: Vect = ORIGIN,
        coor_mask: Iterable = (1, 1, 1),
        root_only: bool = False,
        item_root_only: bool = False,
    ) -> Self:
        '''
        移动到 ``target`` 的位置
        '''
        self.shift(
            self._compute_move_shift(self, target, aligned_edge, coor_mask, root_only, item_root_only),
            root_only=root_only
        )
        return self

    def move_to_by_indicator(
        self,
        indicator: Item,
        target: Item | Vect,
        *,
        aligned_edge: Vect = ORIGIN,
        coor_mask: Iterable = (1, 1, 1),
        root_only: bool = False,
        indicator_root_only: bool = False,
        item_root_only: bool = False
    ) -> Self:
        '''
        与 :meth:`move_to` 类似，但是该方法作用 ``indicator`` 被移动到 ``target`` 所计算出的位移，
        而不是 :meth:`move_to` 中 ``self`` 被移动到 ``target`` 的位移

        例如：

        .. code-block:: python

            t1 = TypstMath('x^2 + y^2')
            t2 = TypstMath('x + y')
            t2.points.move_to_by_indicator(t2[1], t1[2])

        可以将 ``t2`` 移动至 ``t1`` 的位置，
        并且使得 ``t2`` 的加号与 ``t1`` 的加号对齐

        .. note::

            这个示例使用 :meth:`~.TypstDoc.match_pattern` 会更简洁
        '''
        cmpt = self.get_same_cmpt(indicator)
        self.shift(
            cmpt._compute_move_shift(cmpt, target, aligned_edge, coor_mask, indicator_root_only, item_root_only),
            root_only=root_only
        )
        return self

    def align_to(
        self,
        item_or_point: Item | Vect,
        direction: Vect = ORIGIN,
        *,
        root_only: bool = False,
        item_root_only: bool = False,
    ) -> Self:
        '''对齐

        例如，``item1.align_to(item2, UP)`` 会将 ``item1`` 垂直移动，顶部与 ``item2`` 的上边缘对齐
        '''

        if isinstance(item_or_point, Item):
            cmpt = self.get_same_cmpt(item_or_point)
            box = cmpt.self_box if item_root_only else cmpt.box
            point = box.get(direction)
        else:
            point = item_or_point

        for dim in range(3):
            if direction[dim] != 0:
                self.set_coord(point[dim], dim=dim, direction=direction, root_only=root_only)

        return self

    def arrange(
        self,
        direction: Vect = RIGHT,
        center: bool = True,
        **kwargs
    ) -> Self:
        '''
        将子物件按照 ``direction`` 方向排列
        '''
        if self.bind is None:
            return

        cmpts = [
            self.get_same_cmpt(item)
            for item in self.bind.at_item.children
        ]

        for cmpt1, cmpt2 in zip(cmpts, cmpts[1:]):
            cmpt2.next_to(cmpt1.bind.at_item, direction, **kwargs)

        if center:
            self.to_center()

        return self

    @staticmethod
    def _format_rows_cols(
        items_count: int,
        n_rows: int | None,
        n_cols: int | None,
    ) -> tuple[int, int]:
        if n_rows is None and n_cols is None:
            n_rows = int(np.sqrt(items_count))
        if n_rows is None:
            n_rows = items_count // n_cols
        if n_cols is None:
            n_cols = items_count // n_rows
        return n_rows, n_cols

    @staticmethod
    def _format_buff(
        buff: float | None = None,
        h_buff: float | None = None,
        v_buff: float | None = None,
        by_center_point: bool = False,
    ) -> tuple[float, float]:
        default_buff = DEFAULT_ITEM_TO_EDGE_BUFF if by_center_point else DEFAULT_ITEM_TO_ITEM_BUFF
        if buff is not None:
            h_buff = buff
            v_buff = buff
        else:
            if h_buff is None:
                h_buff = default_buff
            if v_buff is None:
                v_buff = default_buff

        return h_buff, v_buff

    def arrange_in_grid(
        self,
        n_rows: int | None = None,
        n_cols: int | None = None,

        buff: float | None = None,
        h_buff: float | None = None,
        v_buff: float | None = None,

        aligned_edge: np.ndarray = ORIGIN,
        by_center_point: bool = False,
        fill_rows_first: bool = True
    ) -> Self:
        '''
        将子物件按网格方式排列

        - ``n_rows``, ``n_cols``: 行数、列数
        - ``v_buff``, ``h_buff``: 行距、列距
        - ``aligned_edge``: 对齐边缘
        - ``by_center_point``: 默认为 ``False``；若设置为 ``True``，则仅将物件视为中心点，不考虑物件的宽高
        '''
        if self.bind is None:
            return

        cmpts = [
            self.get_same_cmpt(item)
            for item in self.bind.at_item.children
        ]

        n_rows, n_cols = self._format_rows_cols(len(cmpts), n_rows, n_cols)
        h_buff, v_buff = self._format_buff(buff, h_buff, v_buff, by_center_point)

        x_unit, y_unit = h_buff, v_buff
        if not by_center_point:
            x_unit += max([cmpt.box.width for cmpt in cmpts])
            y_unit += max([cmpt.box.height for cmpt in cmpts])

        for index, cmpt in enumerate(cmpts):
            if fill_rows_first:
                x, y = index % n_cols, index // n_cols
            else:
                x, y = index // n_rows, index % n_rows
            cmpt.move_to(ORIGIN, aligned_edge=aligned_edge)
            cmpt.shift(x * x_unit * RIGHT + y * y_unit * DOWN)

        self.to_center()
        return self

    def arrange_by_offset(
        self,
        offset: Vect,
        *,
        aligned_edge: Vect = ORIGIN,
        center: bool = True
    ) -> Self:
        if self.bind is None or not self.bind.at_item.children:
            return self

        cmpts = [
            self.get_same_cmpt(item)
            for item in self.bind.at_item.children
        ]
        offset = np.array(offset)

        for cmpt1, cmpt2 in zip(cmpts, cmpts[1:]):
            delta = cmpt2.box.get(aligned_edge) - cmpt1.box.get(aligned_edge)
            cmpt2.shift(offset - delta)

        if center:
            self.to_center()

        return self

    def to_center(self, *, root_only=False) -> Self:
        '''
        移动到原点 ``(0, 0, 0)``
        '''
        self.shift(-self.box.center, root_only=root_only)
        return self

    def to_border(
        self,
        direction: Vect,
        buff: float = DEFAULT_ITEM_TO_EDGE_BUFF
    ) -> Self:
        '''
        移动到视框的边界
        '''
        target_point = np.sign(direction) * (Config.get.frame_x_radius, Config.get.frame_y_radius, 0)
        point_to_align = self.box.get(direction)
        shift_val = target_point - point_to_align - buff * np.array(direction)
        shift_val = shift_val * abs(np.sign(direction))
        self.shift(shift_val)
        return self

    @staticmethod
    def _compute_next_to_shift(
        src: Cmpt_Points,
        target: Item | Vect,
        direction: Vect,
        buff: float,
        aligned_edge: Vect,
        coor_mask: Iterable,
        root_only: bool,
        item_root_only: bool
    ) -> np.ndarray:
        if isinstance(target, Item):
            cmpt = src.get_same_cmpt(target)
            box = cmpt.self_box if item_root_only else cmpt.box
            target = box.get(aligned_edge + direction)

        direction = np.asarray(direction)

        point_to_align = (src.self_box if root_only else src.box).get(aligned_edge - direction)
        return (target - point_to_align + buff * direction) * coor_mask

    def next_to(
        self,
        target: Item | Vect,
        direction: Vect = RIGHT,
        *,
        buff: float = DEFAULT_ITEM_TO_ITEM_BUFF,
        aligned_edge: Vect = ORIGIN,
        coor_mask: Iterable = (1, 1, 1),
        root_only: bool = False,
        item_root_only: bool = False,
    ) -> Self:
        '''
        将该物件放到 ``target`` 旁边
        '''
        self.shift(
            self._compute_next_to_shift(self, target,
                                        direction, buff, aligned_edge, coor_mask,
                                        root_only, item_root_only),
            root_only=root_only
        )
        return self

    def next_to_by_indicator(
        self,
        indicator: Item,
        target: Item | Vect,
        direction: Vect = RIGHT,
        *,
        buff: float = DEFAULT_ITEM_TO_ITEM_BUFF,
        aligned_edge: Vect = ORIGIN,
        coor_mask: Iterable = (1, 1, 1),
        root_only: bool = False,
        indicator_root_only: bool = False,
        item_root_only: bool = False,
    ) -> Self:
        '''
        与 :meth:`next_to` 类似，但是该方法作用 ``indicator`` 被放到 ``target`` 旁边所计算出的位移，
        而不是 :meth:`move_to` 中 ``self`` 被放到 ``target`` 旁边的位移

        例如：

        .. code-block:: python

            t1 = Typst('x^2 + y^2')
            t2 = Typst('x + y z w')
            t2.points.next_to_by_indicator(t2[1], t1[2], DOWN)

        可以将 ``t1`` 对齐到 ``t2`` 的下方，
        并且使得 ``t1`` 的加号在 ``t2`` 的加号的正下方

        .. note::

            这个示例也可以使用字符索引
        '''
        cmpt = self.get_same_cmpt(indicator)
        self.shift(
            self._compute_next_to_shift(cmpt, target,
                                        direction, buff, aligned_edge, coor_mask,
                                        indicator_root_only, item_root_only),
            root_only=root_only
        )
        return self

    def shift_onto_screen(self, **kwargs) -> Self:
        space_lengths = [Config.get.frame_x_radius, Config.get.frame_y_radius]
        buff = kwargs.get("buff", DEFAULT_ITEM_TO_EDGE_BUFF)
        for vect in UP, DOWN, LEFT, RIGHT:
            dim = np.argmax(np.abs(vect))
            max_val = space_lengths[dim] - buff
            edge_center = self.box.get(vect)
            if np.dot(edge_center, vect) > max_val:
                self.to_border(vect, **kwargs)
        return self

    def shift_onto_screen_along_direction(
        self,
        direction: Vect,
        *,
        buff: float = DEFAULT_ITEM_TO_EDGE_BUFF
    ) -> Self:
        center = self.box.center
        x_radius = Config.get.frame_x_radius - self.box.width / 2 - buff
        y_radius = Config.get.frame_y_radius - self.box.height / 2 - buff

        # 如果已经在内部了，那么就不用移动了
        if -x_radius <= center[0] <= x_radius and -y_radius <= center[1] <= y_radius:
            return self

        # (X, Y, Distance)
        candidates: list[tuple[float, float, float]] = []

        # 计算 direction 方向的直线与两条竖线的交点
        for x in (-x_radius, x_radius):
            # 如果 direction 几乎垂直，那么直接将横向吸附点加到 candidates 中
            # 否则就计算交点加到 candidates 中
            if np.isclose(direction[0], 0):
                y = center[1]
                dist = abs(x - center[0])
            else:
                y = center[1] + direction[1] * (x - center[0]) / direction[0]
                if -y_radius <= y <= y_radius:
                    dist = 0
                else:
                    dist = min(abs(y + y_radius), abs(y - y_radius))

            candidates.append((x, clip(y, -y_radius, y_radius), dist))

        # 计算 direction 方向的直线与两条横线的交点
        for y in (-y_radius, y_radius):
            # 如果 direction 几乎水平，那么直接将纵向吸附点加到 candidates 中
            # 否则就计算交点加到 candidates 中
            if np.isclose(direction[1], 0):
                x = center[0]
                dist = abs(y - center[1])
            else:
                x = center[0] + direction[0] * (y - center[1]) / direction[1]
                if -x_radius <= x <= x_radius:
                    dist = 0
                else:
                    dist = min(abs(x + x_radius), abs(x - x_radius))

            candidates.append((clip(x, -x_radius, x_radius), y, dist))

        # 筛选出最佳的位置
        min_dist = min(p[2] for p in candidates)
        filtered = [p for p in candidates if np.isclose(p[2], min_dist)]
        best = min(filtered, key=lambda p: get_norm(p[:2] - center[:2]))

        self.move_to([*best[:2], center[2]])
        return self

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

    # endregion
