from __future__ import annotations
from typing import Iterable, Callable, Optional
import itertools as it
import numpy as np
import sys
import copy

from janim.constants import *
from janim.utils.functions import safe_call
from janim.utils.math_functions import rotation_matrix
from janim.utils.color import hex_to_rgb
from janim.utils.iterables import resize_array
from janim.utils.bezier import interpolate, integer_interpolate
from janim.constants import *

from janim.shaders.render import RenderData, Renderer

class Item:
    comment = ''

    color = WHITE

    def __init__(self) -> None:
        # 基本结构
        self.parent: Item = None
        self.items: list[Item] = []

        # 点坐标数据
        self.points = np.zeros((0, 3), dtype=np.float32)    # points 在所有操作中都会保持 dtype=np.float32，以便传入 shader

        # 颜色数据
        self.rgbas = np.array([1, 1, 1, 1], dtype=np.float32).reshape((1, 4))   # rgbas 在所有操作中都会保持 dtype=np.float32，以便传入 shader
        self.needs_new_rgbas = True

        # 边界箱
        # self.needs_new_bbox = True
        # self.bbox = np.zeros((3, 3))

        # 渲染
        self.renderer = self.create_renderer()

        # 默认值
        self.set_color(self.color)

    #region 响应

    def points_count_changed(self) -> None:
        self.needs_new_rgbas = True
    
    def points_changed(self) -> None:
        self.renderer.needs_update = True
    
    def rgbas_changed(self) -> None:
        self.renderer.needs_update = True
    
    #endregion

    #region 基本结构（array-like 操作、物件包含关系）

    def __getitem__(self, value):
        if isinstance(value, slice):
            return MethodGroup(*self.items[value])
        return self.items[value]

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def add(self, *items: Item):
        for item in items:                  # 遍历要追加的每个物件
            if item in self:                    # 如果已经是子物件，则跳过
                continue
            if item.parent:                    # 将当前物件已有的父物件解除
                item.parent.remove(item)
            self.items.append(item)            # 设置当前物件的父物件
            item.parent = self
        return self

    def remove(self, *items: Item):
        for item in items:          # 遍历要移除的每个物件
            if item not in self:        # 如果不是子物件，则跳过
                continue
            item.parent = None         # 将当前物件移出
            self.items.remove(item)
        return self
    
    def get_family(self) -> list[Item]:
        # TODO: optimize
        sub_families = (item.get_family() for item in self.items)
        return [self, *it.chain(*sub_families)]
    
    #endregion

    #region 基本操作

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

    def arrange_in_grid(self):
        # TODO: arrange_in_grid
        pass

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
        return len(self.points)
    
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

    def set_rgbas(self, rgbas: Iterable[Iterable[float, float, float, float]]):
        rgbas = resize_array(np.array(rgbas), max(1, self.points_count()))
        if len(rgbas) == len(self.rgbas):
            self.rgbas[:] = rgbas
        else:
            self.rgbas = rgbas.astype(np.float32)
        self.rgbas_changed()
        return self
    
    def set_color(
        self, 
        color: JAnimColor | Iterable[JAnimColor], 
        opacity: float | Iterable[float] = 1
    ):
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
        color = resize_array(np.array(color), max(1, self.points_count()))
        
        if not isinstance(opacity, Iterable):
            opacity = [opacity]
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

    def set_opacity(self, opacity: float | Iterable[float]):
        if not isinstance(opacity, Iterable):
            opacity = [opacity]
        opacity = resize_array(np.array(opacity), len(self.rgbas))
        self.rgbas[:, 3] = opacity
        self.rgbas_changed()
        return self

    #endregion

    #region 边界箱 bounding_box
    
    def get_bbox(self) -> np.ndarray:
        # TODO: optimize
        return self.compute_bbox()
        
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
        # TODO: subitem_to_align
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
        return self.comment
    
    def print_family(self, include_self=True, sub_prefix=''):
        if include_self:
            print(self)

        for i, item in enumerate(self):
            comment = item.get_comment()
            if item is not self.items[-1]:
                print(f'{sub_prefix}├──\033[34m[{i}]\033[0m {item} \033[30m({comment})\033[0m')
                item.print_family(False, sub_prefix + '│   ')
            else:
                print(f'{sub_prefix}└──\033[34m[{i}]\033[0m {item} \033[30m({comment})\033[0m')
                item.print_family(False, sub_prefix + '    ')
        
        return self

    #endregion  


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

