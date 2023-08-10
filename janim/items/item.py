from __future__ import annotations
from typing import Iterable, Callable, Optional
from janim.typing import Self

import itertools as it
import numpy as np
import sys
import copy
import inspect

from janim.constants import *
from janim.utils.space_ops import rotation_matrix, get_norm, angle_of_vector
from janim.utils.color import hex_to_rgb
from janim.utils.iterables import resize_array, resize_preserving_order
from janim.utils.bezier import interpolate, integer_interpolate

TimeBasedUpdaterFn = Callable[["Item", float], None]
NonTimeUpdaterFn = Callable[["Item"], None]
UpdaterFn = Union[TimeBasedUpdaterFn, NonTimeUpdaterFn]

class Item:
    comment = ''

    def __init__(
        self,
        color: JAnimColor = WHITE,
        opacity: float = 1.0,
    ) -> None:
        self.visible = False

        # 基本结构
        from janim.scene.scene import Scene
        self.parent: Item | Scene = None
        self.items: list[Item] = []

        # helper_items 仅被 apply_points_function 所影响
        # （也与 rotate、shift 等变换有关），不参与其它物件有关的操作
        # 比如可以向 helper_items 添加一个 Point，以跟踪变换前后的相对位置
        self.helper_items: list[Item] = []

        # 点坐标数据
        self.points = np.zeros((0, 3), dtype=np.float32)    # points 在所有操作中都会保持 dtype=np.float32，以便传入 shader
        self.bbox = np.zeros((3, 3))

        # 颜色数据
        self.rgbas = np.array([1, 1, 1, 1], dtype=np.float32).reshape((1, 4))   # rgbas 在所有操作中都会保持 dtype=np.float32，以便传入 shader
        self.rgbas_visible = True

        # 其它
        self.flags: dict[str, bool] = {}    # see `.set_flag`
        self.targets: dict[str, Item] = {}  # see `.generate_target`
        self.updaters: list[Updater] = []   # see `.add_updaters`
        self.renderer = self.create_renderer()
        self.npdata_to_copy_and_interpolate: set[tuple[str, str, str]] = set((
            ('points', 'get_points', 'set_points'), 
            ('rgbas', 'get_rgbas', 'set_rgbas')
        ))

        # 默认值
        self.set_points_color(color, opacity)

    #region 响应

    @staticmethod
    def mark_flag(func: Callable, key: str = '', flag: bool = True) -> None:
        func.__self__.flags[f'{func.__name__}_{key}'] = flag
    
    @staticmethod
    def check_flag(func: Callable, key: str = '') -> bool:
        return func.__self__.flags.get(key, True)

    @staticmethod
    def take_flag(func: Callable, key: str = '') -> bool:
        key = f'{func.__name__}_{key}'
        flags = func.__self__.flags
        res = flags.get(key, True)
        flags[key] = False
        return res
    
    def take_self_flag(self, key: str = '') -> bool:
        name = inspect.currentframe().f_back.f_code.co_name
        key = f'{name}_{key}'
        res = self.flags.get(key, True)
        self.flags[key] = False
        return res

    def items_changed(self) -> None:
        self.mark_needs_new_family()
        self.mark_needs_new_family_with_helpers()
    
    def helper_items_changed(self) -> None:
        self.mark_needs_new_family_with_helpers()

    def points_count_changed(self) -> None:
        self.mark_flag(self.get_rgbas)
    
    def points_changed(self) -> None:
        self.mark_needs_new_bbox()
        self.mark_flag(self.get_points, 'render')
        self.renderer.needs_update = True
    
    def rgbas_changed(self) -> None:
        self.mark_flag(self.get_rgbas_visible)
        self.mark_flag(self.get_rgbas, 'render')
        self.renderer.needs_update = True
    
    #endregion

    #region 物件包含关系

    def add(self, *items: Item, inhert_visible: bool = True, is_helper: bool = False) -> Self:
        target = self.helper_items if is_helper else self.items

        for item in items:                  # 遍历要追加的每个物件
            if item in self:                    # 如果已经是子物件，则跳过
                continue
            if item.parent is not None:         # 将当前物件已有的父物件解除
                item.parent.remove(item)
            target.append(item)                 # 设置当前物件的父物件
            item.parent = self

            if inhert_visible and self.visible:
                item.set_visible(True)

        if is_helper:
            self.helper_items_changed()
        else:
            self.items_changed()
        return self
    
    def add_to_front(self, item: Item) -> Self:
        if item.parent is not None:
            item.parent.remove(item)
        self.add(item)
        return self
    
    def add_to_back(self, item: Item) -> Self:
        if item.parent is not None:
            item.parent.remove(item)
        self.items.insert(0, item)
        item.parent = self
        self.items_changed()
        return self

    def remove(self, *items: Item, is_helper: bool = False) -> Self:
        target = self.helper_items if is_helper else self.items

        for item in items:          # 遍历要移除的每个物件
            if item not in self:        # 如果不是子物件，则跳过
                continue
            item.parent = None          # 将当前物件移出
            target.remove(item)

        if is_helper:
            self.helper_items_changed()
        else:
            self.items_changed()
        return self
    
    def replace_subitem(self, item: Item, target: Item) -> Self:
        if item in self.items and target not in self.items:
            item.parent = None
            self.items[self.items.index(item)] = target
            target.parent = self
            self.items_changed()
        return self
    
    def set_subitems(self, subitem_list: list[Item]) -> Self:
        self.remove(*self.items)
        self.add(*subitem_list)
        return self
    
    def mark_needs_new_family(self) -> None:
        self.mark_flag(self.get_family)
        if self.parent is not None and isinstance(self.parent, Item):
            self.parent.mark_needs_new_family()

    def mark_needs_new_family_with_helpers(self) -> None:
        self.mark_flag(self.get_family_with_helpers)
        if self.parent is not None and isinstance(self.parent, Item):
            self.parent.mark_needs_new_family_with_helpers()
    
    def get_family(self) -> list[Item]:
        if self.take_self_flag():
            sub_families = (item.get_family() for item in self.items)
            self.family = [self, *it.chain(*sub_families)]
        return self.family
    
    def family_members_with_points(self) -> list[Item]:
        return [m for m in self.get_family() if m.has_points()]
    
    def get_family_with_helpers(self) -> list[Item]:
        if self.take_self_flag():
            sub_families = (
                item.get_family_with_helpers() 
                for item in it.chain(self.items, self.helper_items)
            )
            self.family_with_helpers = [self, *it.chain(*sub_families)]
        return self.family_with_helpers

    def get_toplevel_item(self) -> Item:
        item = self
        while isinstance(item, Item) and item.parent is not None:
            item = item.parent
        return item

    #endregion

    #region 基本操作

    def __getitem__(self, value) -> Item | NoRelGroup:
        if isinstance(value, slice):
            return NoRelGroup(*self.items[value])
        return self.items[value]

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __str__(self) -> str:
        return self.__class__.__name__

    def __mul__(self, times: int) -> Group:
        assert(isinstance(times, int))
        return Group(
            *(self.copy() for _ in range(times))
        )

    def copy(self) -> Self:
        copy_item = copy.copy(self)

        # relation
        copy_item.parent = None
        copy_item.items = []
        copy_item.add(*[m.copy() for m in self])
        copy_item.helper_items = []
        copy_item.add(*[m.copy() for m in self.helper_items], is_helper=True)

        # data
        for key, getter, setter in self.npdata_to_copy_and_interpolate:
            setattr(copy_item, key, getattr(self, key).copy())

        # other
        copy_item.flags = {}
        copy_item.renderer = copy_item.create_renderer()

        return copy_item
    
    def set_visible(
        self, 
        visible, 
        recurse_up: bool = False, 
        recurse_down: bool = True
    ) -> Self:
        self.visible = visible
        if recurse_up and self.parent is not None and isinstance(self.parent, Item):
            self.parent.set_visible(visible, True, False)
        if recurse_down:
            for item in self.items:
                item.set_visible(visible, False, True)

    def generate_target(self, key: str = '') -> Self:
        target = self.copy()
        self.targets[key] = target
        return target
    
    def save_state(self, key: str = '') -> Self:
        self.generate_target('saved_state_' + key)
        return self
    
    def restore(self, key: str = '') -> Self:
        key = 'saved_state_' + key
        if key not in self.targets:
            raise Exception('Trying to restore without having saved')
        self.become(self.targets[key])
        return self
    
    def become(self, item: Item) -> Self:
        self.align_family(item)
        for item1, item2 in zip(self.get_family(), item.get_family()):
            for key, getter, setter in item1.npdata_to_copy_and_interpolate & item2.npdata_to_copy_and_interpolate:
                getattr(item1, setter)(getattr(item2, getter)())
        return self
    
    def arrange(
        self,
        direction: np.ndarray = RIGHT,
        center: bool = True,
        **kwargs
    ) -> Self:
        for m1, m2 in zip(self, self[1:]):
            m2.next_to(m1, direction, **kwargs)
        if center:
            self.to_center()
        return self
    
    @staticmethod
    def format_rows_cols(
        items_count: int, 
        n_rows: Optional[int],
        n_cols: Optional[int],
    ) -> tuple[int, int]:
        if n_rows is None and n_cols is None:
            n_rows = int(np.sqrt(items_count))
        if n_rows is None:
            n_rows = items_count // n_cols
        if n_cols is None:
            n_cols = items_count // n_rows
        return n_rows, n_cols
    
    @staticmethod
    def format_buff(
        buff: Optional[float] = None,
        h_buff: Optional[float] = None,
        v_buff: Optional[float] = None,
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
        n_rows: Optional[int] = None,
        n_cols: Optional[int] = None,

        buff: Optional[float] = None,
        h_buff: Optional[float] = None,
        v_buff: Optional[float] = None,

        aligned_edge: np.ndarray = ORIGIN,
        by_center_point: bool = False,
        fill_rows_first: bool = True
    ) -> Self:
        n_rows, n_cols = self.format_rows_cols(len(self.items), n_rows, n_cols)
        h_buff, v_buff = self.format_buff(buff, h_buff, v_buff, by_center_point)
        
        x_unit, y_unit = h_buff, v_buff
        if not by_center_point:
            x_unit += max([item.get_width() for item in self.items])
            y_unit += max([item.get_height() for item in self.items])

        for index, item in enumerate(self.items):
            if fill_rows_first:
                x, y = index % n_cols, index // n_cols
            else:
                x, y = index // n_rows, index % n_rows
            item.move_to(ORIGIN, aligned_edge)
            item.shift(x * x_unit * RIGHT + y * y_unit * DOWN)
        self.to_center()
        return self
    
    @staticmethod
    def arrange_by_array(
        items_array: Iterable[Iterable[Item]],

        buff: Optional[float] = None,
        h_buff: Optional[float] = None,
        v_buff: Optional[float] = None,

        aligned_edge: np.ndarray = ORIGIN,
        by_center_point: bool = False
    ) -> None:
        h_buff, v_buff = Item.format_buff(buff, h_buff, v_buff, by_center_point)

        x_unit, y_unit = h_buff, v_buff
        flatten = NoRelGroup(*[item for item in list(it.chain(*items_array)) if item is not None])
        if not by_center_point:
            x_unit += max([item.get_width() for item in flatten])
            y_unit += max([item.get_height() for item in flatten])
        
        for row, line in enumerate(items_array):
            for col, item in enumerate(line):
                if item is None:
                    continue
                item.move_to(ORIGIN, aligned_edge)
                item.shift(col * x_unit * RIGHT + row * y_unit * DOWN)
        
        flatten.to_center()
        

    #endregion

    #region 点坐标数据

    def set_points(self, points: Iterable) -> Self:
        '''
        设置点坐标数据，每个坐标点都有三个分量
        
        使用形如 `set_points([[1.5, 3, 2], [2, 1.5, 0]])` 的形式
        '''
        if not isinstance(points, np.ndarray):
            points = np.array(points)
        if len(points) == 0:
            self.clear_points()
            return self
        assert(points.ndim == 2)
        assert(points.shape[1] == 3)
        
        if len(points) == len(self.points):
            self.points[:] = points
        else:
            self.points = points.astype(np.float32)
            self.points_count_changed()
        self.points_changed()
        return self
    
    def get_points(self) -> np.ndarray:
        return self.points
    
    def get_all_points(self) -> np.ndarray:
        return np.vstack([
            self.get_points(),
            *(
                item.get_all_points()
                for item in self
            )
        ])

    def append_points(self, points: Iterable) -> Self:
        '''
        追加点坐标数据，每个坐标点都有三个分量

        使用形如 `append_points([[1.5, 3, 2], [2, 1.5, 0]])` 的形式
        '''
        if not isinstance(points, np.ndarray):
            points = np.array(points)
        assert(points.ndim == 2)
        assert(points.shape[1] == 3)

        self.points = np.append(self.points, points.astype(np.float32), axis=0)
        self.points_count_changed()
        self.points_changed()
        return self

    def match_points(self, item: Item) -> Self:
        '''
        将另一个物件的点坐标数据设置到该物件上
        '''
        self.set_points(item.get_points())
        return self

    def clear_points(self) -> Self:
        self.points = np.zeros((0, 3), dtype=np.float32)
        self.points_count_changed()
        self.points_changed()
        return self

    def reverse_points(self, recurse=True) -> Self:
        if recurse:
            for item in self.items:
                item.reverse_points()
        self.set_points(self.get_points()[::-1])
        self.set_rgbas(self.get_rgbas()[::-1])
        return self
    
    def resize_points(
        self,
        new_length: int,
        resize_func: Callable[[np.ndarray, int], np.ndarray] = resize_array
    ) -> Self:
        self.set_points(resize_func(self.get_points(), new_length))
        return self
    
    def points_count(self) -> int:
        return len(self.get_points())
    
    def has_points(self) -> bool:
        return self.points_count() > 0
    
    def get_start(self) -> np.ndarray:
        self.throw_error_if_no_points()
        return self.get_points()[0].copy()

    def get_end(self) -> np.ndarray:
        self.throw_error_if_no_points()
        return self.get_points()[-1].copy()

    def get_start_and_end(self) -> tuple(np.ndarray, np.ndarray):
        self.throw_error_if_no_points()
        points = self.get_points()
        return (points[0].copy(), points[-1].copy())

    def point_from_proportion(self, alpha: float) -> np.ndarray:
        points = self.get_points()
        i, subalpha = integer_interpolate(0, len(points) - 1, alpha)
        return interpolate(points[i], points[i + 1], subalpha)

    def pfp(self, alpha) -> np.ndarray:
        """Abbreviation for point_from_proportion"""
        return self.point_from_proportion(alpha)
    
    def throw_error_if_no_points(self) -> None:
        if not self.has_points():
            message = "Cannot call Item.{} " +\
                      "for a Item with no points"
            caller_name = sys._getframe(1).f_code.co_name
            raise Exception(message.format(caller_name))

    #endregion

    #region 边界箱 bounding_box

    def mark_needs_new_bbox(self) -> None:
        self.mark_flag(self.get_bbox)
        if self.parent is not None and isinstance(self.parent, Item):
            self.parent.mark_needs_new_bbox()
    
    def get_bbox(self) -> np.ndarray:
        if self.take_self_flag():
            self.bbox = self.compute_bbox()
        return self.bbox
        
    def compute_bbox(self) -> np.ndarray:
        all_points = np.vstack([
            self.get_points(),
            *(
                item.get_bbox()
                for item in self.get_family()[1:]
                if item.has_points()
            )
        ])
        if len(all_points) == 0:
            return np.zeros((3, 3))
        
        mins = all_points.min(0)
        maxs = all_points.max(0)
        mids = (mins + maxs) / 2
        return np.array([mins, mids, maxs])

    def get_bbox_point(self, direction: np.ndarray) -> np.ndarray:
        bb = self.get_bbox()
        indices = (np.sign(direction) + 1).astype(int)
        return np.array([
            bb[indices[i]][i]
            for i in range(3)
        ])
    
    def get_continuous_bbox_point(self, direction: np.ndarray) -> np.ndarray:
        dl, center, ur = self.get_bbox()
        corner_vect = (ur - center)
        return center + direction / np.max(np.abs(np.true_divide(
            direction, corner_vect,
            out=np.zeros(len(direction)),
            where=((corner_vect) != 0)
        )))
    
    def get_top(self) -> np.ndarray:
        return self.get_bbox_point(UP)

    def get_bottom(self) -> np.ndarray:
        return self.get_bbox_point(DOWN)

    def get_right(self) -> np.ndarray:
        return self.get_bbox_point(RIGHT)

    def get_left(self) -> np.ndarray:
        return self.get_bbox_point(LEFT)

    def get_zenith(self) -> np.ndarray:
        return self.get_bbox_point(OUT)

    def get_nadir(self) -> np.ndarray:
        return self.get_bbox_point(IN)
    
    def get_center(self) -> np.ndarray:
        return self.get_bbox()[1]

    def length_over_dim(self, dim: int) -> float:
        bb = self.get_bbox()
        return abs((bb[2] - bb[0])[dim])
    
    def get_width(self) -> float:
        return self.length_over_dim(0)

    def get_height(self) -> float:
        return self.length_over_dim(1)

    def get_depth(self) -> float:
        return self.length_over_dim(2)
    
    def get_coord(self, dim: int, direction: np.ndarray = ORIGIN) -> float:
        """
        Meant to generalize get_x, get_y, get_z
        """
        return self.get_bbox_point(direction)[dim]

    def get_x(self, direction=ORIGIN) -> float:
        return self.get_coord(0, direction)

    def get_y(self, direction=ORIGIN) -> float:
        return self.get_coord(1, direction)

    def get_z(self, direction=ORIGIN) -> float:
        return self.get_coord(2, direction)

    #endregion

    #region 颜色数据

    @staticmethod
    def format_color(color: JAnimColor | Iterable[JAnimColor] | None) -> Iterable | None:
        if color is None:
            return None
        if isinstance(color, str):
            color = [hex_to_rgb(color)]
        elif isinstance(color, Iterable) and not any(isinstance(v, Iterable) for v in color):
            color = [color]
        else:
            color = [
                hex_to_rgb(c) 
                if isinstance(c, str) else c 
                for c in color
            ]

        return color
    
    @staticmethod
    def format_opacity(opacity: float | Iterable[float] | None) -> Iterable | None:
        if opacity is None:
            return None
        if not isinstance(opacity, Iterable):
            opacity = [opacity]
        return opacity

    def set_rgbas(self, rgbas: Iterable[Iterable[float, float, float, float]]) -> Self:
        rgbas = np.array(rgbas, dtype=np.float32)
        assert(rgbas.ndim == 2)
        assert(rgbas.shape[1] == 4)
        
        rgbas = resize_array(rgbas, max(1, self.points_count()))
        if len(rgbas) == len(self.rgbas):
            self.rgbas[:] = rgbas
        else:
            self.rgbas = rgbas
        self.rgbas_changed()
        return self
    
    def set_points_color(
        self, 
        color: Optional[JAnimColor | Iterable[JAnimColor]] = None, 
        opacity: Optional[float | Iterable[float]] = None,
        recurse: bool = True,
    ) -> Self:
        color, opacity = self.format_color(color), self.format_opacity(opacity)

        if recurse:
            for item in self:
                item.set_points_color(color, opacity)

        if color is None:
            color = self.get_rgbas()[:, :3]
        if opacity is None:
            opacity = self.get_rgbas()[:, 3]

        color = resize_array(np.array(color), max(1, self.points_count()))
        opacity = resize_array(np.array(opacity), max(1, self.points_count()))
        self.set_rgbas(
            np.hstack((
                color, 
                opacity.reshape((len(opacity), 1))
            ))
        )

        return self

    def get_rgbas(self) -> np.ndarray:
        if self.take_self_flag():
            self.set_rgbas(self.rgbas)
        return self.rgbas
    
    def set_opacity(self, opacity: float, recurse: bool = True) -> Self:
        self.set_points_color(opacity=opacity)
        if recurse:
            for item in self.items:
                item.set_opacity(opacity)
        return self
    
    def is_transparent(self) -> bool:
        data = self.get_rgbas()[:, 3]
        return np.any((0 < data) & (data < 1))

    def get_rgbas_visible(self) -> bool:
        if self.take_self_flag():
            self.rgbas_visible = self.compute_rgbas_visible()
        return self.rgbas_visible
    
    def compute_rgbas_visible(self) -> bool:
        return np.any(self.get_rgbas()[:, 3] > 0)

    #endregion

    #region updater

    def update(self, dt: float, recurse: bool = True) -> Self:
        for updater in self.updaters:
            updater.do(dt)
        
        if recurse:
            for item in self.items:
                item.update(dt, recurse)
        return self

    def add_updater(self, fn: UpdaterFn) -> Updater:
        for updater in self.updaters:
            if fn is updater.fn:
                return updater
        updater = Updater(self, fn)
        self.updaters.append(updater)
        return updater
    
    def remove_updater(self, updater_or_fn: Updater | UpdaterFn) -> Self:
        for updater in self.updaters:
            if updater is updater_or_fn or updater.fn is updater_or_fn:
                self.updaters.remove(updater)
                break
        return self

    #endregion

    #region 变换

    def apply_points_function(
        self,
        func: Callable[[np.ndarray], np.ndarray],
        about_point: np.ndarray = None,
        about_edge: np.ndarray = ORIGIN
    ) -> Self:
        if about_point is None and about_edge is not None:
            about_point = self.get_bbox_point(about_edge)
        
        for item in self.get_family_with_helpers():
            if not item.has_points():
                continue
            if about_point is None:
                item.set_points(func(item.get_points()))
            else:
                item.set_points(func(item.get_points() - about_point) + about_point)

        return self
    
    def apply_function(
        self, 
        function: Callable[[np.ndarray], np.ndarray],
        about_point: np.ndarray = ORIGIN,
        **kwargs
    ) -> Self:
        # Default to applying matrix about the origin, not mobjects center
        self.apply_points_function(
            lambda points: np.array([function(p) for p in points]),
            about_point=about_point,
            **kwargs
        )
        return self

    def apply_matrix(self, matrix: Iterable, **kwargs) -> Self:
        # Default to applying matrix about the origin, not mobjects center
        if ("about_point" not in kwargs) and ("about_edge" not in kwargs):
            kwargs["about_point"] = ORIGIN
        full_matrix = np.identity(3)
        matrix = np.array(matrix)
        full_matrix[:matrix.shape[0], :matrix.shape[1]] = matrix
        self.apply_points_function(
            lambda points: np.dot(points, full_matrix.T),
            **kwargs
        )
        return self
    
    def apply_complex_function(self, function: Callable[[complex], complex], **kwargs) -> Self:
        def R3_func(point):
            x, y, z = point
            xy_complex = function(complex(x, y))
            return [
                xy_complex.real,
                xy_complex.imag,
                z
            ]
        return self.apply_function(R3_func, **kwargs)

    def rotate(
        self,
        angle: float,
        axis: np.ndarray = OUT,
        about_point: Optional[np.ndarray] = None,
        **kwargs
    ) -> Self:
        rot_matrix_T = rotation_matrix(angle, axis).T
        self.apply_points_function(
            lambda points: np.dot(points, rot_matrix_T),
            about_point,
            **kwargs
        )
        return self
    
    def scale(
        self,
        scale_factor: float | Iterable,
        min_scale_factor: float = 1e-8,
        about_point: Optional[np.ndarray] = None,
        about_edge: np.ndarray = ORIGIN
    ) -> Self:
        if isinstance(scale_factor, Iterable):
            scale_factor = np.array(scale_factor).clip(min=min_scale_factor)
        else:
            scale_factor = max(scale_factor, min_scale_factor)
        
        self.apply_points_function(
            lambda points: scale_factor * points,
            about_point=about_point,
            about_edge=about_edge
        )
        return self
    
    def stretch(self, factor: float, dim: int, **kwargs) -> Self:
        def func(points):
            points[:, dim] *= factor
            return points
        self.apply_points_function(func, **kwargs)
        return self
    
    def rescale_to_fit(self, length: float, dim: int, stretch: bool = False, **kwargs) -> Self:
        old_length = self.length_over_dim(dim)
        if old_length == 0:
            return self
        if stretch:
            self.stretch(length / old_length, dim, **kwargs)
        else:
            self.scale(length / old_length, **kwargs)
        return self
    
    def set_width(self, width: float, stretch: bool = False, **kwargs) -> Self:
        return self.rescale_to_fit(width, 0, stretch=stretch, **kwargs)

    def set_height(self, height: float, stretch: bool = False, **kwargs) -> Self:
        return self.rescale_to_fit(height, 1, stretch=stretch, **kwargs)

    def set_depth(self, depth: float, stretch: bool = False, **kwargs) -> Self:
        return self.rescale_to_fit(depth, 2, stretch=stretch, **kwargs)
    
    def set_size(
        self,
        width: Optional[float] = None,
        height: Optional[float] = None,
        depth: Optional[float] = None,
        **kwargs
    ) -> Self:
        if width:
            self.set_width(width, True, **kwargs)
        if height:
            self.set_height(height, True, **kwargs)
        if depth:
            self.set_depth(depth, True, **kwargs)
        return self
    
    def replace(self, item: Item, dim_to_match: int = 0, stretch: bool = False) -> Self:
        if not item.points_count() and not item.items:
            self.scale(0)
            return self
        if stretch:
            for i in range(3):
                self.rescale_to_fit(item.length_over_dim(i), i, stretch=True)
        else:
            self.rescale_to_fit(
                item.length_over_dim(dim_to_match),
                dim_to_match,
                stretch=False
            )
        self.shift(item.get_center() - self.get_center())
        return self
    
    def put_start_and_end_on(self, start: np.ndarray, end: np.ndarray) -> Self:
        curr_start, curr_end = self.get_start_and_end()
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

    #endregion

    #region 位移

    def shift(self, vector: np.ndarray) -> Self:
        self.apply_points_function(
            lambda points: points + vector,
            about_edge=None
        )
        return self
    
    def move_to(
        self,
        target: Item | np.ndarray,
        aligned_edge: np.ndarray = ORIGIN,
        coor_mask: Iterable = (1, 1, 1)
    ) -> Self:
        if isinstance(target, Item):
            target = target.get_bbox_point(aligned_edge)
        point_to_align = self.get_bbox_point(aligned_edge)
        self.shift((target - point_to_align) * coor_mask)
        return self

    def to_center(self) -> Self:
        self.shift(-self.get_center())
        return self

    def to_border(
        self,
        direction: np.ndarray,
        buff: float = DEFAULT_ITEM_TO_EDGE_BUFF
    ) -> Self:
        """
        Direction just needs to be a vector pointing towards side or
        corner in the 2d plane.
        """
        target_point = np.sign(direction) * (FRAME_X_RADIUS, FRAME_Y_RADIUS, 0)
        point_to_align = self.get_bbox_point(direction)
        shift_val = target_point - point_to_align - buff * np.array(direction)
        shift_val = shift_val * abs(np.sign(direction))
        self.shift(shift_val)
        return self
    
    def next_to(
        self,
        target: Item | np.ndarray,
        direction: np.ndarray = RIGHT,
        buff: float = DEFAULT_ITEM_TO_ITEM_BUFF,
        aligned_edge: np.ndarray = ORIGIN,
        coor_mask: Iterable = (1, 1, 1)
    ) -> Self:
        if isinstance(target, Item):
            target = target.get_bbox_point(aligned_edge + direction)
        
        point_to_align = self.get_bbox_point(aligned_edge - direction)
        self.shift((target - point_to_align + buff * direction) * coor_mask)
        return self
    
    def set_coord(self, value: float, dim: int, direction: np.ndarray = ORIGIN) -> Self:
        curr = self.get_coord(dim, direction)
        shift_vect = np.zeros(3)
        shift_vect[dim] = value - curr
        self.shift(shift_vect)
        return self

    def set_x(self, x: float, direction: np.ndarray = ORIGIN) -> Self:
        return self.set_coord(x, 0, direction)

    def set_y(self, y: float, direction: np.ndarray = ORIGIN) -> Self:
        return self.set_coord(y, 1, direction)

    def set_z(self, z: float, direction: np.ndarray = ORIGIN) -> Self:
        return self.set_coord(z, 2, direction)

    #endregion

    #region Alignment

    def align_for_transform(self, item: Item):
        self.align_family(item)
        self.align_data(item)
        return self
    
    def align_family(self, item: Item):
        n1 = len(self)
        n2 = len(item)
        if n1 != n2:
            self.add_n_more_subitems(max(0, n2 - n1))
            item.add_n_more_subitems(max(0, n1 - n2))
        # Recurse
        for item1, item2 in zip(self, item):
            item1.align_family(item2)
        return self
    
    def align_data(self, item: Item) -> None:
        for item1, item2 in zip(self.get_family(), item.get_family()):
            item1.align_points(item2)
            for key, getter, setter in item1.npdata_to_copy_and_interpolate & item2.npdata_to_copy_and_interpolate:
                if key == 'points':
                    continue
                getter1, setter1 = getattr(item1, getter), getattr(item1, setter)
                getter2, setter2 = getattr(item2, getter), getattr(item2, setter)
                arr1 = getter1()
                arr2 = getter2()
                if len(arr2) > len(arr1):
                    setter1(resize_preserving_order(arr1, len(arr2)))
                elif len(arr1) > len(arr2):
                    setter2(resize_preserving_order(arr2, len(arr1)))
    
    def align_points(self, item: Item):
        max_len = max(self.points_count(), item.points_count())
        for mob in (self, item):
            mob.resize_points(max_len, resize_func=resize_preserving_order)
        return self

    def add_n_more_subitems(self, n: int):
        if n == 0:
            return self

        curr = len(self)
        if curr == 0:
            # If empty, simply add n point mobjects
            null_item = self.copy()
            null_item.set_points([self.get_center()])
            self.set_subitems([
                null_item.copy()
                for _ in range(n)
            ])
            return self

        target = curr + n
        repeat_indices = (np.arange(target) * curr) // target
        split_factors = [
            (repeat_indices == i).sum()
            for i in range(curr)
        ]
        new_subitems = []
        for subitem, sf in zip(self.items, split_factors):
            transparent = subitem.is_transparent()
            new_subitems.append(subitem)
            for _ in range(1, sf):
                new_subitem = subitem.copy()
                if transparent:
                    new_subitem.set_opacity(0)
                new_subitems.append(new_subitem)
        self.set_subitems(new_subitems)
        return self

    #endregion

    #region Animation

    def anim(self, call_immediately=False, **kwargs) -> Self:
        '''
        通过链式调用创建动画
        - 在默认情况下，变换将基于物体在该动画开始时的状态
        - 若传入 `call_immediately=True`，则变换将基于物体一开始的状态

        ```python
        # 例如下面代码，对于第二个动画，它会基于物体在 1s 时的状态，也就是第一个动画完成后的状态，进行变换
        # 如果这里传入 `call_immediately=True`，那么就会重新从物体一开始的白色空心六边形状态进行变换
        poly = RegularPolygon()
        self.add(poly)
        self.play(
            poly.anim()                             .scale(2).rotate(30 * DEGREES),
            poly.anim(begin_time=1)                 .scale(0.8).set_color(BLUE).set_fill(opacity=0.5),
            poly.anim(begin_time=2.2, run_time=0.5) .scale(1 / 0.8).set_color(RED)
        )
        ```
        '''

        # 实际上返回的是 `MethodAnimation`，但假装返回了 `self`，以做到代码提示
        from janim.animation.transform import MethodAnimation
        return MethodAnimation(self, call_immediately=call_immediately, **kwargs)

    def interpolate(
        self,
        item1: Item,
        item2: Item,
        alpha: float,
        path_func: Callable[[np.ndarray, np.ndarray, float], np.ndarray],
        npdata_to_copy_and_interpolate: Optional[list[tuple[str, str, str]]] = None
    ) -> Self:
        if npdata_to_copy_and_interpolate is None:
            npdata_to_copy_and_interpolate = item1.npdata_to_copy_and_interpolate & item2.npdata_to_copy_and_interpolate

        for key, getter, setter in npdata_to_copy_and_interpolate:
            setter_self = getattr(self, setter)
            getter1 = getattr(item1, getter)
            getter2 = getattr(item2, getter)
            func = path_func if key == 'points' else interpolate
            setter_self(func(getter1(), getter2(), alpha))
        
        return self

    #endregion

    #region 渲染

    def create_renderer(self):
        from janim.gl.render import Renderer
        return Renderer()

    def render(self, data) -> None:
        if not self.renderer or not self.visible:
            return
        
        self.renderer.prepare(self)
        self.renderer.pre_render(self, data)

        for item in self:
            item.render(data)

        self.renderer.render(self, data)
        
    #endregion

    #region 辅助功能

    def get_comment(self) -> str:
        return self.comment or f'points: {self.points_count()}'
    
    def print_family_structure(self, include_self=True, sub_prefix='') -> Self:
        if include_self:
            print(f'{self} \033[30m({self.get_comment()})\033[0m')

        for i, item in enumerate(self):
            comment = item.get_comment()
            if item is not self.items[-1]:
                print(f'{sub_prefix}├──\033[34m[{i}]\033[0m {item} \033[30m({comment})\033[0m')
                item.print_family_structure(False, sub_prefix + '│   ')
            else:
                print(f'{sub_prefix}└──\033[34m[{i}]\033[0m {item} \033[30m({comment})\033[0m')
                item.print_family_structure(False, sub_prefix + '    ')
        
        return self

    #endregion

class Updater:
    def __init__(self, item: Item, fn: UpdaterFn) -> None:
        self.item = item
        self.fn = fn
        self.is_time_based = self.get_is_time_based(fn)
        self.suspended = False
    
    @staticmethod
    def get_is_time_based(fn: UpdaterFn) -> bool:
        return len(inspect.signature(fn).parameters) == 2
    
    def suspend(self) -> Self:
        self.suspended = True
        return self
    
    def resume(self) -> Self:
        self.suspended = False
    
    def do(self, dt) -> Self:
        if not self.suspended:
            if self.is_time_based:
                self.fn(self.item, dt)
            else:
                self.fn(self.item)
        return self
    
    def remove(self) -> None:
        self.item.remove_updater(self)


class Point(Item):
    def __init__(self, pos: Iterable | np.ndarray, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_points([pos])
    
    def get_pos(self) -> np.ndarray:
        return self.get_center()


class Group(Item):
    def __init__(self, *items: Item, **kwargs) -> None:
        if not all(isinstance(item, Item) for item in items):
            raise Exception('All subitems of Group must be Item')
        super().__init__(**kwargs)
        self.add(*items)

class NoRelGroup(Group):
    '''
    除了子物件不会将自己标记为 `parent` 外，其余功能与 `Group` 相同
    '''

    def add(self, *items: Item, is_helper: bool = False) -> Self:
        target = self.helper_items if is_helper else self.items

        for item in items:                  # 遍历要追加的每个物件
            if item in self:                    # 如果已经是子物件，则跳过
                continue
            target.append(item)                 # 仅将当前物件添加到列表中，而不设定 `parent`

        if is_helper:
            self.helper_items_changed()
        else:
            self.items_changed()
        return self
    
    def remove(self, *items: Item, is_helper: bool = False) -> Self:
        target = self.helper_items if is_helper else self.items

        for item in items:          # 遍历要移除的每个物件
            if item not in self:        # 如果不是子物件，则跳过
                continue
            target.remove(item)

        if is_helper:
            self.helper_items_changed()
        else:
            self.items_changed()
        return self
    
    # 由于子物件没有设定自己为 `parent`，因此原先的一些调用无法正确响应
    # 因此需每次重新计算：
    #   get_family
    #   get_family_with_helpers
    #   get_bbox
    
    def get_family(self) -> list[Item]:
        sub_families = (item.get_family() for item in self.items)
        self.family = [self, *it.chain(*sub_families)]
        return self.family
    
    def get_family_with_helpers(self) -> list[Item]:
        sub_families = (
            item.get_family_with_helpers() 
            for item in it.chain(self.items, self.helper_items)
        )
        self.family_with_helpers = [self, *it.chain(*sub_families)]
        return self.family_with_helpers
    
    def get_bbox(self) -> np.ndarray:
        self.bbox = self.compute_bbox()
        return self.bbox
    

