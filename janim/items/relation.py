from __future__ import annotations

from typing import Callable, Generic, TypeVar, Generator, Type

import janim.utils.refresh as refresh
from janim.typing import Self
from janim.utils.signal import Signal

GRelT = TypeVar('GRelT', bound='Relation')
RelT = TypeVar('RelT', bound='Relation')


class Relation(Generic[GRelT], refresh.Refreshable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.parents: list[GRelT] = []
        self.children: list[GRelT] = []

    def mark_refresh(self, func: Callable | str, *, recurse_up=False, recurse_down=False) -> Self:
        super().mark_refresh(func)

        name = func.__name__ if isinstance(func, Callable) else func

        if recurse_up:
            for obj in self.ancestors():
                if hasattr(obj, name):
                    obj.mark_refresh(name)

        if recurse_down:
            for obj in self.descendants():
                if hasattr(obj, name):
                    obj.mark_refresh(name)

    @Signal
    def parents_changed(self) -> None:
        Relation.parents_changed.emit(self)

    @Signal
    def children_changed(self) -> None:
        Relation.children_changed.emit(self)

    def add(self, *objs: RelT) -> Self:
        '''
        向该物件添加子物件

        Add objects to this item.
        '''
        for obj in objs:
            # 理论上这里判断 item not in self.children 就够了
            # 但是防止有被私自修改 self.parents 以及 self.children 的可能
            # 所以这里都判断了
            if obj not in self.children:
                self.children.append(obj)
            if self not in obj.parents:
                obj.parents.append(self)

        self.children_changed()
        obj.parents_changed()
        return self

    def remove(self, *objs: RelT) -> Self:
        '''
        从该物件移除子物件

        Remove objects from this item.
        '''
        for obj in objs:
            # 理论上这里判断 item in self.children 就够了
            # 原因同 add
            try:
                self.children.remove(obj)
            except ValueError: ...
            try:
                obj.parents.remove(self)
            except ValueError: ...

        self.children_changed()
        obj.parents_changed()
        return self

    def _family(self, *, up: bool) -> list[GRelT]:  # use DFS
        lst = self.parents if up else self.children
        res = []

        for sub_obj in lst:
            res.append(sub_obj)
            res.extend(filter(
                lambda obj: obj not in res,
                sub_obj._family(up=up)
            ))

        return res

    @parents_changed.self_refresh_of_relation(recurse_down=True)
    @refresh.register
    def ancestors(self) -> list[GRelT]:
        return self._family(up=True)

    @children_changed.self_refresh_of_relation(recurse_up=True)
    @refresh.register
    def descendants(self) -> list[GRelT]:
        return self._family(up=False)

    @staticmethod
    def _walk_lst(base_cls: Type[RelT] | None, lst: list[GRelT]) -> Generator[RelT, None, None]:
        if base_cls is None:
            base_cls = Relation

        for obj in lst:
            if isinstance(obj, base_cls):
                yield obj

    def walk_ancestors(self, base_cls: Type[RelT] = None) -> Generator[RelT, None, None]:
        yield from self._walk_lst(base_cls, self.ancestors())

    def walk_descendants(self, base_cls: Type[RelT] = None) -> Generator[RelT, None, None]:
        yield from self._walk_lst(base_cls, self.descendants())
