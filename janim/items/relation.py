from __future__ import annotations

import random
from typing import Callable, Generator, Self

import janim.utils.refresh as refresh
from janim.utils.signal import Signal


class Relation[GRelT: 'Relation'](refresh.Refreshable):
    '''
    定义了有向无环图的包含关系以及一些实用操作

    也就是，对于每个对象：

    - ``self.parents`` 存储了与其直接关联的父对象
    - ``self.children`` 存储了与其直接关联的子对象
    - 使用 :meth:`add()` 建立对象间的关系
    - 使用 :meth:`remove()` 取消对象间的关系
    - :meth:`ancestors()` 表示与其直接关联的祖先对象（包括父对象，以及父对象的父对象，......）
    - :meth:`descendants()` 表示与其直接关联的后代对象（包括子对象、以及子对象的子对象，......）
    - 对于 :meth:`ancestors()` 以及 :meth:`descendants()`：
        - 不包含调用者自身并且返回的列表中没有重复元素
        - 物件顺序是 DFS 顺序
    '''
    def __init__(self):
        super().__init__()

        self.parents: list[GRelT] = []
        '''
        .. warning::

            不要直接对该变量作出修改，请使用 :meth:`add` 和 :meth:`remove` 等方法

            对该变量的直接访问仅是为了方便遍历等操作
        '''

        self.children: list[GRelT] = []
        '''
        .. warning::

            不要直接对该变量作出修改，请使用 :meth:`add` 和 :meth:`remove` 等方法

            对该变量的直接访问仅是为了方便遍历等操作
        '''

    def mark_refresh(self, func: Callable | str, *, recurse_up=False, recurse_down=False) -> Self:
        super().mark_refresh(func)

        name = func.__name__ if callable(func) else func

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
        '''
        信号，在 ``self.parents`` 改变时触发
        '''
        Relation.parents_changed.emit(self)

    @Signal
    def children_changed(self) -> None:
        '''
        信号，在 ``self.children`` 改变时触发
        '''
        Relation.children_changed.emit(self)

    def add(self, *objs: GRelT, insert=False) -> Self:
        '''
        向该对象添加子对象

        如果 ``insert=True`` （默认为 ``False``），那么插入到子物件列表的开头
        '''
        for obj in (reversed(objs) if insert else objs):
            # 理论上这里判断 item not in self.children 就够了，但是防止
            # 有被私自修改 self.parents 以及 self.children 的可能，所以这里都判断了
            # Theoretically, checking item not in self.children is enough here, but to prevent
            # possible modifications to self.parents and self.children, both checks are made here.
            if obj not in self.children:
                if insert:
                    self.children.insert(0, obj)
                else:
                    self.children.append(obj)
            if self not in obj.parents:
                obj.parents.append(self)
            obj.parents_changed()

        self.children_changed()
        return self

    def remove(self, *objs: GRelT) -> Self:
        '''
        从该对象移除子对象
        '''
        for obj in objs:
            # 理论上这里判断 `item in self.children` 就够了，原因同 `add`
            # Theoretically, checking `item in self.children` is enough here, for the same reason as `add`.
            try:
                self.children.remove(obj)
            except ValueError: ...
            try:
                obj.parents.remove(self)
            except ValueError: ...
            obj.parents_changed()

        self.children_changed()
        return self

    def shuffle(self) -> Self:
        random.shuffle(self.children)
        self.children_changed()
        return self

    def clear_parents(self) -> Self:
        for parent in self.parents:
            parent.remove(self)
        return self

    def clear_children(self) -> Self:
        self.remove(*self.children)
        return self

    def _family(self, *, up: bool) -> list[GRelT]:  # use DFS
        lst = self.parents if up else self.children
        res = []

        for sub_obj in lst:
            if sub_obj not in res:
                res.append(sub_obj)
            res.extend(filter(
                lambda obj: obj not in res,
                sub_obj._family(up=up)
            ))

        return res

    @parents_changed.self_refresh_with_recurse(recurse_down=True)
    @refresh.register
    def ancestors(self) -> list[GRelT]:
        '''
        获得祖先对象列表
        '''
        return self._family(up=True)

    @children_changed.self_refresh_with_recurse(recurse_up=True)
    @refresh.register
    def descendants(self) -> list[GRelT]:
        '''
        获得后代对象列表
        '''
        return self._family(up=False)

    @staticmethod
    def _walk_lst[RelT](base_cls: type[RelT] | None, lst: list[GRelT]) -> Generator[RelT, None, None]:
        if base_cls is None:
            yield from lst
            return

        for obj in lst:
            if isinstance(obj, base_cls):
                yield obj

    def _walk_nearest_family[RelT](
        self: Relation,
        base_cls: type[RelT],
        fn_family: Callable[[Relation], list[Relation]],
    ) -> Generator[RelT, None, None]:

        lst = fn_family(self)[:]

        while lst:
            obj = lst.pop(0)
            if isinstance(obj, base_cls):
                # DFS 结构保证了使用该做法进行剔除的合理性
                # DFS structure ensures the validity of using this method for removal.
                for sub_obj in fn_family(obj):
                    if not lst:
                        break
                    if lst[0] is sub_obj:
                        lst.pop(0)
                yield obj

    def walk_ancestors[RelT](self, base_cls: type[RelT] = None) -> Generator[RelT, None, None]:
        '''
        遍历祖先节点中以 ``base_cls`` （缺省则遍历全部）为基类的对象
        '''
        yield from self._walk_lst(base_cls, self.ancestors())

    def walk_descendants[RelT](self, base_cls: type[RelT] = None) -> Generator[RelT, None, None]:
        '''
        遍历后代节点中以 ``base_cls`` （缺省则遍历全部）为基类的对象
        '''
        yield from self._walk_lst(base_cls, self.descendants())

    def walk_self_and_ancestors(self, root_only=False) -> Generator[GRelT, None, None]:
        '''
        遍历自己以及祖先节点
        '''
        yield self
        if not root_only:
            yield from self.ancestors()

    def walk_self_and_descendants(self, root_only=False) -> Generator[GRelT, None, None]:
        '''
        遍历自己以及后代节点
        '''
        yield self
        if not root_only:
            yield from self.descendants()

    def walk_nearest_ancestors[RelT](self, base_cls: type[RelT]) -> Generator[RelT, None, None]:
        '''
        遍历祖先节点中以 ``base_cls`` 为基类的对象，但是排除已经满足条件的对象的祖先对象
        '''
        yield from self._walk_nearest_family(base_cls, lambda rel: rel.ancestors())

    def walk_nearest_descendants[RelT](self, base_cls: type[RelT]) -> Generator[RelT, None, None]:
        '''
        遍历后代节点中以 ``base_cls`` 为基类的对象，但是排除已经满足条件的对象的后代对象
        '''
        yield from self._walk_nearest_family(base_cls, lambda rel: rel.descendants())
