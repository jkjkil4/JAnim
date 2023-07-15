from __future__ import annotations
from typing import Iterable, Callable, Optional, Tuple
import itertools as it
import numpy as np
import sys
import copy

from janim.constants import *
from janim.utils.functions import safe_call
from janim.utils.space_ops import rotation_matrix, get_norm, angle_of_vector
from janim.utils.color import hex_to_rgb
from janim.utils.iterables import resize_array
from janim.utils.bezier import interpolate, integer_interpolate

from janim.shaders.render import RenderData, Renderer

class Item:
    comment = ''

    def __init__(
        self,
        color: JAnimColor = WHITE,
        opacity: float = 1.0
    ) -> None:
        # 基本结构
        self.parent: Item = None
        self.items: list[Item] = []
        self.needs_new_family = True

        # helper_items 仅被 apply_points_function 所影响（也与 rotate、
        # shift 等变换有关）不参与其它物件有关的操作
        # 比如可以向 helper_items 添加一个 Point，以跟踪变换前后的相对位置
        self.helper_items: list[Item] = []

        # 点坐标数据
        self.points = np.zeros((0, 3), dtype=np.float32)    # points 在所有操作中都会保持 dtype=np.float32，以便传入 shader
        self.needs_new_bbox = True

        # 颜色数据
        self.rgbas = np.array([1, 1, 1, 1], dtype=np.float32).reshape((1, 4))   # rgbas 在所有操作中都会保持 dtype=np.float32，以便传入 shader
        self.needs_new_rgbas = True

        # 边界箱
        self.bbox = np.zeros((3, 3))
        self.needs_new_bbox = True

        # 渲染
        self.renderer = self.create_renderer()

        # 默认值
        self.set_points_color(color, opacity)

    #region 响应

    def items_changed(self) -> None:
        self.needs_new_family = True

    def points_count_changed(self) -> None:
        self.needs_new_rgbas = True
    
    def points_changed(self) -> None:
        self.needs_new_bbox = True
        self.renderer.needs_update = True
    
    def rgbas_changed(self) -> None:
        self.renderer.needs_update = True
    
    #endregion

    #region 物件包含关系

    def add(self, *items: Item, is_helper: bool = False):
        target = self.helper_items if is_helper else self.items

        for item in items:                  # 遍历要追加的每个物件
            if item in self:                    # 如果已经是子物件，则跳过
                continue
            if item.parent:                     # 将当前物件已有的父物件解除
                item.parent.remove(item)
            target.append(item)                 # 设置当前物件的父物件
            item.parent = self
        self.items_changed()
        return self

    def remove(self, *items: Item, is_helper: bool = False):
        target = self.helper_items if is_helper else self.items

        for item in items:          # 遍历要移除的每个物件
            if item not in self:        # 如果不是子物件，则跳过
                continue
            item.parent = None          # 将当前物件移出
            target.remove(item)
        self.items_changed()
        return self
    
    def get_family(self) -> list[Item]:
        if self.needs_new_family:
            sub_families = (item.get_family() for item in self.items)
            self.family = [self, *it.chain(*sub_families)]
        return self.family
    
    def family_members_with_points(self) -> list[Item]:
        return [m for m in self.get_family() if m.has_points()]
    
    def add_helper_items(self, *items: Item):
        for item in items:
            if item in self:
                continue
            self.helper_items.append(item)
        return self
    
    def remove_helper_items(self, *items: Item):
        for item in items:
            if item not in self:
                continue
            self.helper_items.remove(item)
        return self

    #endregion

    #region 基本操作

    def __getitem__(self, value) -> Item | MethodGroup:
        if isinstance(value, slice):
            return MethodGroup(*self.items[value])
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

    def copy(self):
        copy_item = copy.copy(self)

        # relation
        copy_item.parent = None
        copy_item.items = []
        copy_item.add(*[m.copy() for m in self])

        # data
        copy_item.points = self.points.copy()
        copy_item.rgbas = self.rgbas.copy()

        # render
        copy_item.renderer = copy_item.create_renderer()

        return copy_item
    
    def arrange(
        self,
        direction: np.ndarray = RIGHT,
        center: bool = True,
        **kwargs
    ):
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
    ):
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
    ):
        default_buff = DEF_ITEM_TO_EDGE_BUFF if by_center_point else DEF_ITEM_TO_ITEM_BUFF
        if buff is not None:
            h_buff = buff
            v_buff = buff
        else:
            if h_buff is None:
                h_buff = default_buff
            if v_buff is None:
                v_buff = default_buff
        
        return h_buff, v_buff
        
    # TODO: arrange_by_array
    
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
    ):
        n_rows, n_cols = self.format_rows_cols(len(self.items), n_rows, n_cols)
        h_buff, v_buff = self.format_buff(buff, h_buff, v_buff, by_center_point)
        
        x_unit = h_buff
        y_unit = v_buff
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

    #endregion

    #region 点坐标数据

    def set_points(self, points: Iterable):
        '''
        设置点坐标数据，每个坐标点都有三个分量
        
        使用形如 `set_points([[1.5, 3, 2], [2, 1.5, 0]])` 的形式
        '''
        if not isinstance(points, np.ndarray):
            points = np.array(points)
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

    def append_points(self, points: Iterable):
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

    def match_points(self, item: Item):
        '''
        将另一个物件的点坐标数据设置到该物件上
        '''
        self.set_points(item.get_points())
        return self

    def clear_points(self):
        self.points = np.zeros((0, 3), dtype=np.float32)
        self.points_count_changed()
        self.points_changed()
        return self

    def reverse_points(self, recurse=True):
        if recurse:
            for item in self.items:
                safe_call(item, 'reverse_points')
        self.set_points(self.get_points()[::-1])
        self.set_rgbas(self.get_rgbas()[::-1])
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

    def pfp(self, alpha):
        """Abbreviation for point_from_proportion"""
        return self.point_from_proportion(alpha)
    
    def throw_error_if_no_points(self):
        if not self.has_points():
            message = "Cannot call Item.{} " +\
                      "for a Item with no points"
            caller_name = sys._getframe(1).f_code.co_name
            raise Exception(message.format(caller_name))

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

    def set_rgbas(self, rgbas: Iterable[Iterable[float, float, float, float]]):
        rgbas = resize_array(np.array(rgbas), max(1, self.points_count()))
        if len(rgbas) == len(self.rgbas):
            self.rgbas[:] = rgbas
        else:
            self.rgbas = rgbas.astype(np.float32)
        self.rgbas_changed()
        return self
    
    def set_points_color(
        self, 
        color: Optional[JAnimColor | Iterable[JAnimColor]] = None, 
        opacity: Optional[float | Iterable[float]] = None,
        recurse: bool = True,
    ):
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
        if self.needs_new_rgbas:
            self.set_rgbas(self.rgbas)
            self.needs_new_rgbas = False
        return self.rgbas

    #endregion

    #region 边界箱 bounding_box
    
    def get_bbox(self) -> np.ndarray:
        if self.needs_new_bbox:
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

    #region 变换

    def apply_points_function(
        self,
        func: Callable[[np.ndarray], np.ndarray],
        about_point: np.ndarray = None,
        about_edge: np.ndarray = ORIGIN
    ):
        if about_point is None and about_edge is not None:
            about_point = self.get_bbox_point(about_edge)
        
        for item in self.get_family():
            if not item.has_points():
                continue
            if about_point is None:
                item.set_points(func(item.get_points()))
            else:
                item.set_points(func(item.get_points() - about_point) + about_point)
        
        for item in self.helper_items:
            item.apply_points_function(func, about_point)

        return self

    def rotate(
        self,
        angle: float,
        axis: np.ndarray = OUT,
        about_point: Optional[np.ndarray] = None,
        **kwargs
    ):
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
    ):
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
    
    def stretch(self, factor: float, dim: int, **kwargs):
        def func(points):
            points[:, dim] *= factor
            return points
        self.apply_points_function(func, **kwargs)
        return self
    
    def rescale_to_fit(self, length: float, dim: int, stretch: bool = False, **kwargs):
        old_length = self.length_over_dim(dim)
        if old_length == 0:
            return self
        if stretch:
            self.stretch(length / old_length, dim, **kwargs)
        else:
            self.scale(length / old_length, **kwargs)
        return self
    
    def set_width(self, width: float, stretch: bool = False, **kwargs):
        return self.rescale_to_fit(width, 0, stretch=stretch, **kwargs)

    def set_height(self, height: float, stretch: bool = False, **kwargs):
        return self.rescale_to_fit(height, 1, stretch=stretch, **kwargs)

    def set_depth(self, depth: float, stretch: bool = False, **kwargs):
        return self.rescale_to_fit(depth, 2, stretch=stretch, **kwargs)
    
    def set_size(
        self,
        width: Optional[float] = None,
        height: Optional[float] = None,
        depth: Optional[float] = None,
        **kwargs
    ):
        if width:
            self.set_width(width, True, **kwargs)
        if height:
            self.set_height(height, True, **kwargs)
        if depth:
            self.set_depth(depth, True, **kwargs)
    
    def replace(self, item: Item, dim_to_match: int = 0, stretch: bool = False):
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
    
    def put_start_and_end_on(self, start: np.ndarray, end: np.ndarray):
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

    def shift(self, vector: np.ndarray):
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
    ):
        if isinstance(target, Item):
            target = target.get_bbox_point(aligned_edge)
        point_to_align = self.get_bbox_point(aligned_edge)
        self.shift((target - point_to_align) * coor_mask)
        return self

    def to_center(self):
        self.shift(-self.get_center())
        return self

    def to_border(
        self,
        direction: np.ndarray,
        buff: float = DEF_ITEM_TO_EDGE_BUFF
    ):
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
        buff: float = DEF_ITEM_TO_ITEM_BUFF,
        aligned_edge: np.ndarray = ORIGIN,
        coor_mask: Iterable = (1, 1, 1)
    ):
        if isinstance(target, Item):
            target = target.get_bbox_point(aligned_edge + direction)
        
        point_to_align = self.get_bbox_point(aligned_edge - direction)
        self.shift((target - point_to_align + buff * direction) * coor_mask)
        return self
    
    def set_coord(self, value: float, dim: int, direction: np.ndarray = ORIGIN):
        curr = self.get_coord(dim, direction)
        shift_vect = np.zeros(3)
        shift_vect[dim] = value - curr
        self.shift(shift_vect)
        return self

    def set_x(self, x: float, direction: np.ndarray = ORIGIN):
        return self.set_coord(x, 0, direction)

    def set_y(self, y: float, direction: np.ndarray = ORIGIN):
        return self.set_coord(y, 1, direction)

    def set_z(self, z: float, direction: np.ndarray = ORIGIN):
        return self.set_coord(z, 2, direction)

    #endregion

    #region 渲染

    def create_renderer(self) -> Renderer:
        return Renderer()

    def render(self, data: RenderData) -> None:
        if not self.renderer:
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
    
    def print_family_structure(self, include_self=True, sub_prefix=''):
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


class Point(Item):
    def __init__(self, pos: Iterable | np.ndarray, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_points([pos])
    
    def get_pos(self) -> np.ndarray:
        return self.get_center()


class Group(Item):
    def __init__(self, *items: Item) -> None:
        super().__init__()
        self.add(*items)


class MethodGroup:
    def __init__(self, *items: Item | MethodGroup) -> None:
        self.items = items
    
    def __getattr__(self, method_name: str):
        def wrap(*method_args, **method_kwargs) -> MethodGroup:
            for item in self.items:
                if isinstance(item, MethodGroup):
                    method = getattr(item, method_name)
                    method(*method_args, **method_kwargs)
                elif hasattr(item, method_name):
                    method = getattr(item, method_name)
                    if callable(method):
                        method(*method_args, **method_kwargs)
            return self
        return wrap

    def __getitem__(self, value):
        if isinstance(value, slice):
            return MethodGroup(*self.items[value])
        return self.items[value]

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

