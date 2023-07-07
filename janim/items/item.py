from __future__ import annotations
from typing import List, Iterable, Callable
import itertools as it
import numpy as np

from janim.utils.functions import safe_call
from janim.constants import *
from janim.shaders.render import RenderData, Renderer

class Item:
    comment = ''

    def __init__(self) -> None:
        # relation
        self._parent: Item = None
        self._items: List[Item] = []

        # data
        self._points = np.zeros((0, 3), dtype=np.float32)   # _points 在所有操作中都会保持 dtype=np.float32，以便传入 shader

        self.renderer = self.create_renderer()

    #region 基本结构（array-like 操作、物件包含关系）

    def __getitem__(self, value):
        if isinstance(value, slice):
            return MethodGroup(*self._items[value])
        return self._items[value]

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def add(self, *items: Item):
        for item in items:                  # 遍历要追加的每个物件
            if item in self:                    # 如果已经是子物件，则跳过
                continue
            if item._parent:                    # 将当前物件已有的父物件解除
                item._parent.remove(item)
            self._items.append(item)            # 设置当前物件的父物件
            item._parent = self
        return self

    def remove(self, *items: Item):
        for item in items:          # 遍历要移除的每个物件
            if item not in self:        # 如果不是子物件，则跳过
                continue
            item._parent = None         # 将当前物件移出
            self._items.remove(item)
        return self
    
    def family(self) -> List[Item]:
        # TODO: optimize
        return list(it.chain(*(item.family() for item in self._items)))
    
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
        
        self._points = points.astype(np.float32)
        return self
    
    def get_points(self) -> np.ndarray:
        return self._points

    def append_points(self, points: Iterable):
        '''
        追加点坐标数据，每个坐标点都有三个分量

        使用形如 `append_points([[1.5, 3, 2], [2, 1.5, 0]])` 的形式
        '''
        if not isinstance(points, np.ndarray):
            points = np.array(points)
        assert(points.ndim == 2)
        assert(points.shape[1] == 3)

        self._points = np.append(self._points, points.astype(np.float32), axis=0)
        return self

    def match_points(self, item: Item):
        '''
        将另一个物件的点坐标数据设置到该物件上
        '''
        self.set_points(item.get_points())
        return self

    def clear_points(self):
        self._points = np.zeros((0, 3), dtype=np.float32)
        return self

    def reverse_points(self, recurse=True):
        if recurse:
            for item in self._items:
                safe_call(item, 'reverse_points')
        self._points = self._points[::-1]
    
    def apply_points_function(
        self,
        func: Callable[[np.ndarray], np.ndarray],
        about_point: np.ndarray = None,
        about_edge: np.ndarray = ORIGIN
    ):
        # TODO
        pass

    def points_count(self) -> int:
        return len(self._points)

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
            if item is not self._items[-1]:
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
