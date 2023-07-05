from __future__ import annotations
from typing import List
import itertools as it

class Item:
    def __init__(self, comment='') -> None:
        # conf
        self.comment = comment

        # relation
        self.parent: Item = None
        self.items: List[Item] = []     # 使用 add、remove 来对其进行操作，请勿直接访问

    #region 基本结构

    def __getitem__(self, value):
        if isinstance(value, slice):
            from items.group import MethodGroup
            return MethodGroup(*self.items[value])
        return self.items[value]

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def add(self, *items: Item) -> Item:
        for item in items:
            if item in self:
                continue
            if item.parent:
                item.parent.remove(item)
            self.items.append(item)
            item.parent = self
        return self

    def remove(self, *items: Item) -> Item:
        for item in items:
            if item not in self:
                continue
            item.parent = None
            self.items.remove(item)
        return self
    
    def family(self) -> List[Item]:
        # TODO: optimize
        return list(it.chain(*(item.family() for item in self.items)))
    
    #endregion

    #region 辅助功能

    def get_comment(self) -> str:
        return self.comment
    
    def print_family(self, include_self=True, sub_prefix='') -> Item:
        if include_self:
            print(self.__class__.__name__)

        for i, item in enumerate(self):
            comment = item.get_comment()
            if item is not self.items[-1]:
                print(f'{sub_prefix}├──\033[34m[{i}]\033[0m {item.__class__.__name__} \033[30m({comment})\033[0m')
                item.print_family(False, sub_prefix + '│   ')
            else:
                print(f'{sub_prefix}└──\033[34m[{i}]\033[0m {item.__class__.__name__} \033[30m({comment})\033[0m')
                item.print_family(False, sub_prefix + '    ')
        
        return self

    #endregion