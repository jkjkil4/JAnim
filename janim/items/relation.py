from __future__ import annotations

import random
from typing import Callable, Generator, Self, overload

import janim.utils.refresh as refresh
from janim.utils.deprecation import deprecated
from janim.utils.signal import Signal


# 因为该类其实只用于 Item，所以类方法中的描述都直接使用“物件”了
class Relation[GRelT: 'Relation'](refresh.Refreshable):
    """
    定义了有向无环图的包含关系以及一些实用操作

    也就是，对于每个对象：

    - ``self.parents`` 存储了与其直接关联的父对象
    - ``self.children`` 存储了与其直接关联的子对象
    - 使用 :meth:`add()` 建立对象间的关系
    - 使用 :meth:`remove()` 取消对象间的关系
    - 使用 :meth:`get_parents()` 和 :meth:`get_children()` 获取对象列表的副本
    - :meth:`ancestors()` 表示与其直接关联的祖先对象（包括父对象，以及父对象的父对象，......）
    - :meth:`descendants()` 表示与其直接关联的后代对象（包括子对象、以及子对象的子对象，......）
    - 对于 :meth:`ancestors()` 以及 :meth:`descendants()`：
        - 不包含调用者自身并且返回的列表中没有重复元素
        - 对象顺序是 DFS 顺序
    """
    def __init__(self):
        super().__init__()

        self._parents: list[GRelT] = []
        self._children: list[GRelT] = []

    @property
    def parents(self):
        """
        父物件列表的一份拷贝
        """
        return self._parents.copy()

    @property
    def children(self):
        """
        子物件列表的一份拷贝
        """
        return self._children.copy()

    def __iter__(self):
        return iter(self._children)

    def __contains__(self, obj: GRelT):
        return obj in self._children

    def __len__(self) -> int:
        return len(self._children)

    def index(self, obj: GRelT) -> int:
        """
        获取子物件在列表中的索引位置

        :param obj: 要查找的子物件
        :return: 子物件的索引位置
        :raises ValueError: 子物件不在列表中
        """
        return self._children.index(obj)

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

        return self

    @Signal
    def _parents_changed(self) -> None:
        """
        信号，在 ``self.parents`` 改变时触发
        """
        Relation._parents_changed.emit(self)

    @Signal
    def _children_changed(self) -> None:
        """
        信号，在 ``self.children`` 改变时触发
        """
        Relation._children_changed.emit(self)

    def add(
        self,
        *objs: GRelT,
        prepend=False,
        insert=None    # deprecated
    ) -> Self:
        """
        向该物件添加子物件

        :param objs: 要添加的子物件
        :param prepend: 默认为 ``False``，如果为 ``True``，那么插入到子物件列表的开头
        """
        if insert is not None:
            deprecated(
                'insert',
                'prepend',
                remove=(4, 3)
            )

        for obj in (reversed(objs) if prepend else objs):
            if obj not in self._children:
                if prepend:
                    self._children.insert(0, obj)
                else:
                    self._children.append(obj)

            assert self not in obj._parents
            obj._parents.append(self)
            obj._parents_changed()

        self._children_changed()
        return self

    def insert(self, index: int, *objs: GRelT) -> Self:
        """
        在指定索引位置插入子物件

        :param index: 插入位置的索引
        :param objs: 要插入的子物件
        """
        for i, obj in enumerate(objs):
            if obj not in self._children:
                self._children.insert(index + i, obj)

            assert self not in obj._parents
            obj._parents.append(self)
            obj._parents_changed()

        self._children_changed()
        return self

    def remove(self, *objs: GRelT) -> Self:
        """
        从该物件移除子物件

        :param objs: 要移除的子物件
        """
        for obj in objs:
            try:
                self._children.remove(obj)
                # 如果上面没有抛出 ValueError，说明存在这个关系，这意味着 self 曾记录在 obj._parents 中
                assert self in obj._parents
                obj._parents.remove(self)
                obj._parents_changed()
            except ValueError: ...

        self._children_changed()
        return self

    def shuffle(self) -> Self:
        """
        随机打乱子物件的顺序

        .. note::

            该方法使用 :func:`random.shuffle` 进行随机打乱

            如果需要可重复的随机结果，请在调用此方法前使用 :func:`random.seed` 设置随机数种子
        """
        random.shuffle(self._children)
        self._children_changed()
        return self

    def clear_parents(self) -> Self:
        """
        清空父物件
        """
        for parent in self._parents.copy():
            parent.remove(self)
        return self

    def clear_children(self) -> Self:
        """
        清空子物件
        """
        self.remove(*self._children)
        return self

    def _family(self, *, up: bool) -> list[GRelT]:  # use DFS
        """
        对 :meth:`ancestors` 和 :meth:`descendants` 的通用封装

        :param up: 当该值为 ``False`` 时，即为 :meth:`descendants`；为 ``True`` 时则为 :meth:`ancestors`
        """
        lst = self._parents if up else self._children
        res = []

        for sub_obj in lst:
            if sub_obj not in res:
                res.append(sub_obj)
            res.extend(filter(
                lambda obj: obj not in res,
                sub_obj._family(up=up)
            ))

        return res

    @_parents_changed.self_refresh_with_recurse(recurse_down=True)
    @refresh.register
    def ancestors(self) -> list[GRelT]:
        """
        获得祖先物件列表
        """
        return self._family(up=True)

    @_children_changed.self_refresh_with_recurse(recurse_up=True)
    @refresh.register
    def descendants(self) -> list[GRelT]:
        """
        获得后代物件列表
        """
        return self._family(up=False)

    @overload
    @staticmethod
    def _walk_lst[ListT](base_cls: None, lst: list[ListT]) -> Generator[ListT, None, None]: ...
    @overload
    @staticmethod
    def _walk_lst[ListT, RelT](base_cls: type[RelT], lst: list[ListT]) -> Generator[RelT, None, None]: ...

    @staticmethod
    def _walk_lst[ListT, RelT](base_cls: type[RelT] | None, lst: list[ListT]) -> Generator[ListT | RelT, None, None]:
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

    @overload
    def walk_ancestors(self, base_cls: None = None) -> Generator[GRelT, None, None]: ...
    @overload
    def walk_ancestors[RelT](self, base_cls: type[RelT]) -> Generator[RelT, None, None]: ...

    def walk_ancestors[RelT](self, base_cls: type[RelT] | None = None) -> Generator[GRelT | RelT, None, None]:
        """
        遍历祖先节点中以 ``base_cls`` （缺省则遍历全部）为基类的物件
        """
        yield from self._walk_lst(base_cls, self.ancestors())

    @overload
    def walk_descendants(self, base_cls: None = None) -> Generator[GRelT, None, None]: ...
    @overload
    def walk_descendants[RelT](self, base_cls: type[RelT]) -> Generator[RelT, None, None]: ...

    def walk_descendants[RelT](self, base_cls: type[RelT] | None = None) -> Generator[GRelT | RelT, None, None]:
        """
        遍历后代节点中以 ``base_cls`` （缺省则遍历全部）为基类的物件
        """
        yield from self._walk_lst(base_cls, self.descendants())

    def walk_self_and_ancestors(self, root_only=False) -> Generator[Self | GRelT, None, None]:
        """
        遍历自己以及祖先节点
        """
        yield self
        if not root_only:
            yield from self.ancestors()

    def walk_self_and_descendants(self, root_only=False) -> Generator[Self | GRelT, None, None]:
        """
        遍历自己以及后代节点
        """
        yield self
        if not root_only:
            yield from self.descendants()

    def walk_nearest_ancestors[RelT](self, base_cls: type[RelT]) -> Generator[RelT, None, None]:
        """
        遍历祖先节点中以 ``base_cls`` 为基类的物件，但是排除已经满足条件的物件的祖先物件
        """
        yield from self._walk_nearest_family(base_cls, lambda rel: rel.ancestors())

    def walk_nearest_descendants[RelT](self, base_cls: type[RelT]) -> Generator[RelT, None, None]:
        """
        遍历后代节点中以 ``base_cls`` 为基类的物件，但是排除已经满足条件的物件的后代物件
        """
        yield from self._walk_nearest_family(base_cls, lambda rel: rel.descendants())
