from __future__ import annotations
from typing import Callable, Any, TypeVar
from janim.typing import Self

from functools import wraps
import itertools as it

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
    
    #endregion

class Points:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class _GroupClass(Item):
    def __init__(self, *items: T, **kwargs):
        super().__init__(**kwargs)
        self.add(*items)

    def __getattr__(self, method_name: str) -> Callable:
        '''使得属性的设定可以向子物件传递'''
        def func(*args, **kwargs):
            for item in self.subitems:
                if isinstance(item, _GroupClass) or hasattr(item, method_name):
                    getattr(item, method_name)(*args, **kwargs)
        
        return func

T = TypeVar('T', bound=Item)


# 该方法用于方便类型检查以及补全提示
# 在执行时和直接调用 _GroupClass 没有区别
def Group(*items: T) -> Item | T:
    '''将 `items` 打包为一个 `Group`，方便属性的设定'''
    return _GroupClass(*items)

