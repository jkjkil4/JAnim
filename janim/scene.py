from __future__ import annotations
from typing import List
import itertools as it

from janim.items.item import Item

class Scene:
    def __init__(self) -> None:
        # relation
        self.items: List[Item] = []

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

    def add(self, *items: Item) -> Scene:
        for item in items:
            if item in self:
                continue
            if item.parent:
                item.parent.remove(item)
            self.items.append(item)
            item.parent = self
        return self

    def remove(self, *items: Item) -> Scene:
        for item in items:
            if item not in self:
                continue
            item.parent = None
            self.items.remove(item)
        return self
    
    def get_family(self) -> List[Item]:
        return list(it.chain(*(item.get_family() for item in self.items)))
    
    #endregion
