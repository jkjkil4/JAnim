from __future__ import annotations
from typing import Callable, Any, TypeVar
from janim.typing import Self, VectArray

from functools import wraps
import itertools as it
import copy
import numpy as np
import inspect

from janim.utils.unique_nparray import UniqueNparray

from janim.logger import log

'''
继承 Item 及有关类的注意事项：
    - 完成对 copy 的继承，使得子类的数据能被正常复制
        - 代码结构：

        def copy(self) -> Self:
            copy_item = super().copy()

            # ===========
            # 有关数据复制
            # ===========

            return copy_item
'''

class Item:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.parents: list[Item] = []
        self.subitems: list[Item] = []
        self.markers: list[Points] = []  # TODO: Item.markers

        self.refresh_required: dict[str, bool] = {}
        self.refresh_stored_data: dict[str, Any] = {}

    #region refresh wrapper
        
    '''
    refresh 相关方法
    用于在需要时才进行值的重新计算，提升性能
    
    当一个方法 self.func 被 `register_refresh_required` 修饰后
    会记忆 self.func 被调用后的返回值，并在之后的调用中直接返回该值，而不对 self.func 进行真正的调用
    需要 `mark_refresh_required(self.func)` 才会对 self.func 重新调用以更新返回值

    例如，`get_family` 方法不会每次都进行计算
    只有在 `add` 或 `remove` 执行后，才会将 `get_family` 标记为需要更新
    使得在下次调用 `get_family` 才重新计算结果并返回

    可参考 `test.items.item_test.ItemTest.test_refresh_required`
    '''

    def register_refresh_required(func: Callable) -> Callable:
        '''
        修饰器，标记方法在需要更新时才重新进行计算
        '''
        name = func.__name__

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                is_required = self.refresh_required[name]
            except KeyError:
                is_required = True

            if is_required:
                ret = self.refresh_stored_data[name] = func(self, *args, **kwargs)
                self.refresh_required[name] = False
                return ret
            return self.refresh_stored_data[name]
        
        return wrapper
    
    def mark_refresh_required(self, func: Callable, *, recurse_down: bool = False, recurse_up: bool = False) -> Self:
        '''
        标记指定的 `func` 需要进行更新

        `recurse_down`: 是否递归调用子物件的该方法
        `recurse_up`: 是否递归调用父物件的该方法
        '''
        self.refresh_required[func.__name__] = True
        if recurse_down:
            for item in self.subitems:
                item.mark_refresh_required(func, recurse_down=True)
        if recurse_up:
            for item in self.parents:
                item.mark_refresh_required(func, recurse_up=True)

    #endregion
                
    #region relation
                
    '''
    两个物件之间可以建立 parent-subitem 双向关系
    主要用于 mark_refresh_required 以及一些属性的传递
    并不与渲染顺序直接相关
    '''

    @register_refresh_required
    def get_family(self) -> list[Item]:
        '''获取该物件的所有子物件，即包括自己和子物件的子物件'''
        return [self, *it.chain(*[item.get_family() for item in self.subitems])]

    def add(self, *items: Item) -> Self:
        '''向该物件添加子物件'''
        for item in items:
            # 理论上这里判断 item not in self.subitems 就够了
            # 但是防止有被私自修改 self.parents 以及 self.subitems 的可能
            # 所以这里都判断了
            if item not in self.subitems:
                self.subitems.append(item)
            if self not in item.parents:
                item.parents.append(self)
            
        self.mark_refresh_required(Item.get_family, recurse_up=True)
        return self
    
    def remove(self, *items: Item) -> Self:
        '''从该物件移除子物件'''
        for item in items:
            # 理论上这里判断 item in self.subitems 就够了
            # 原因同 add
            try:
                self.subitems.remove(item)
            except ValueError: ...
            try:
                item.parents.remove(self)
            except ValueError: ...
        
        self.mark_refresh_required(Item.get_family, recurse_up=True)
        return self
    
    def __getitem__(self, value) -> Self:   # 假装返回 Self，用于类型提示
        if isinstance(value, slice):
            return GroupClass(*self.subitems[value])
        return self.subitems[value]
    
    def __iter__(self):
        return iter(self.subitems)
    
    def __len__(self):
        return len(self.subitems)
    
    #endregion

    #region 快速操作

    @property
    def for_all(self) -> Self:  # 假装返回 Self，方便代码补全
        return BatchOp(*self.get_family())

    @property
    def for_all_p(self) -> Self:
        return BatchOp(*self.get_family(), paired=True)
    
    @property
    def for_all_except_self(self) -> Self:
        return BatchOp(*self.get_family()[1:])
    
    @property
    def for_all_except_self_p(self) -> Self:
        return BatchOp(*self.get_family()[1:], paired=True)
    
    @property
    def for_sub(self) -> Self:
        return BatchOp(*self.subitems)
    
    @property
    def for_sub_p(self) -> Self:
        return BatchOp(*self.subitems, paired=True)

    #endregion

    #region 数据复制

    def copy(self) -> Self:
        copy_item = copy.copy(self)
        
        # relation
        copy_item.parents = []
        copy_item.subitems = []
        copy_item.add(*[m.copy() for m in self])
        
        # TODO: copy: markers

        # other
        self.refresh_required.clear()       # 清空，使得所有操作都要重新计算数据
        self.refresh_stored_data.clear()    # 既然 refresh_required 清空了，那么这个就顺便也清空吧，反正也要重新计算的

        return copy_item

    def __mul__(self, times: int) -> Self:  # 假装返回 Self，方便代码补全
        return GroupClass(
            *(self.copy() for _ in range(times))
        )

    #endregion

class Points(Item):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.points = UniqueNparray()

    def copy(self) -> Self:
        copy_item = super().copy()

        copy_item.points = UniqueNparray()
        copy_item.points.data = self.points.data

    #region points

    def points_changed(self) -> None:
        self.mark_refresh_required(self.get_bbox, recurse_up=True)

    def points_count_changed(self) -> None:
        pass

    def get_points(self) -> VectArray:
        return self.points

    def set_points(self, points: VectArray) -> Self:
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

        if len(points) == len(self.points.data):
            self.points = points[:]
        else:
            self.points = points.astype(np.float32)
            self.points_count_changed()
        
        self.points_changed()

        return self
    
    def clear_points(self) -> Self:
        self.set_points(np.zeros((0, 3)))
        return self

    #endregion

class GroupClass(Item):
    def __init__(self, *items: T, **kwargs):
        super().__init__(**kwargs)
        self.add(*items)

T = TypeVar('T', bound=Item)

# 该方法用于方便类型检查以及补全提示
# 在执行时和直接调用 GroupClass 没有区别
def Group(*items: T) -> Item | T:
    '''将 `items` 打包为一个 `Group`，方便属性的设定'''
    return GroupClass(*items)

class BatchOp:
    def __init__(self, *items: Item, paired: bool = False):
        self.items = items
        self.paired = paired
    
    def __getattr__(self, method_name: str):
        def func(*args, **kwargs):
            ret_list = []
            found = False
            for item in self.items:
                if not hasattr(item, method_name):
                    continue
                attr = getattr(item, method_name)

                if not callable(attr):
                    continue
                found = True
                
                ret = attr(*args, **kwargs)
                if ret is not None and ret is not item:
                    ret_list.append((item, ret) if self.paired else ret)

            if not found:
                frame = inspect.currentframe().f_back
                log.warning(f'[{frame.f_code.co_filename}:{frame.f_lineno}] 没有物件拥有 `{method_name}` 方法，调用没有产生效果')

            return ret_list or self
    
        return func
                    


