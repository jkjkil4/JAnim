from __future__ import annotations
from typing import List, Iterable, Callable
import itertools as it
import numpy as np
from functools import wraps

from janim.utils.functions import safe_call
from janim.constants import *
from janim.shaders.render import RenderData, Renderer

class Item:
    comment = ''

    def __init__(self) -> None:
        # 基本结构
        self.parent: Item = None
        self.items: List[Item] = []

        # 点坐标数据
        self.points = np.zeros((0, 3), dtype=np.float32)   # _points 在所有操作中都会保持 dtype=np.float32，以便传入 shader

        # 边界箱
        self.needs_new_bbox = True
        self.bbox = np.zeros((3, 3))

        # 渲染
        self.renderer = self.create_renderer()

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
    
    def family(self) -> List[Item]:
        # TODO: optimize
        return list(it.chain(*(item.family() for item in self.items)))
    
    #endregion

    #region 基本操作

    def __str__(self) -> str:
        return self.__class__.__name__

    def __mul__(self, times: int) -> Group:
        # TODO
        pass

    def copy(self):
        # TODO
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
        
        self.points = points.astype(np.float32)
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
        return self

    def match_points(self, item: Item):
        '''
        将另一个物件的点坐标数据设置到该物件上
        '''
        self.set_points(item.get_points())
        return self

    def clear_points(self):
        self.points = np.zeros((0, 3), dtype=np.float32)
        return self

    def reverse_points(self, recurse=True):
        if recurse:
            for item in self.items:
                safe_call(item, 'reverse_points')
        self.points = self.points[::-1]
    
    def points_count(self) -> int:
        return len(self.points)
    
    def has_points(self) -> bool:
        return self.points_count() > 0

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
                for item in self.family()
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

    #endregion

    #region 变换

    def apply_points_function(
        self,
        func: Callable[[np.ndarray], np.ndarray],
        about_point: np.ndarray = None,
        about_edge: np.ndarray = ORIGIN
    ):
        pass

    #endregion

    #region 渲染

    def create_renderer(self) -> Renderer:
        return None

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
