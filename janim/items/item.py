from __future__ import annotations
from typing import Callable, Any, TypeVar
from janim.typing import Self

from functools import wraps
import itertools as it

import contextvars
import inspect

class Item:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.parents: list[Item] = []
        self.subitems: list[Item] = []
        self.markers: list[Points] = []  # TODO: Item.markers

        self.refresh_required: dict[str, bool] = {}
        self.refresh_stored_data: dict[str, Any] = {}

        fast_parent_tpl = Item.fast_relation_contextvar.get()
        if fast_parent_tpl is not None:
            parent, frame = fast_parent_tpl
            if frame is inspect.currentframe().f_back:
                parent.add(self)

    #region refresh wrapper

    def register_refresh_required(func: Callable) -> Callable:
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
        self.refresh_required[func.__name__] = True
        if recurse_down:
            for item in self.subitems:
                item.mark_refresh_required(func, recurse_down=True)
        if recurse_up:
            for item in self.parents:
                item.mark_refresh_required(func, recurse_up=True)

    #endregion
                
    #region relation
    
    #region basic

    @register_refresh_required
    def get_family(self) -> list[Item]:
        return [self, *it.chain(*[item.get_family() for item in self.subitems])]

    def add(self, *items: Item) -> Self:
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

    #region fast-relation

    fast_relation_contextvar = contextvars.ContextVar('fast_relation', default=None)

    def __enter__(self):
        self.fast_relation_token = Item.fast_relation_contextvar.set((self, inspect.currentframe().f_back))
    
    def __exit__(self, exc_type, exc_value, traceback):
        Item.fast_relation_contextvar.reset(self.fast_relation_token)

    #endregion
    
    #endregion

class Points:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)



