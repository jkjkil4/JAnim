from __future__ import annotations

import random
from typing import (
    Any,
    Callable,
    Generator,
    Iterable,
    Iterator,
    Self,
    SupportsIndex,
    overload,
)

from janim_backend import relation

from janim.exception import RelationError
from janim.locale import get_translator

_ = get_translator('janim.items.relation')

_items_relation_registry = relation.RelationRegistry()


class ItemRelation[RelT: 'ItemRelation']:
    """
    定义了物件的有向无环图的包含关系以及一些实用操作

    该类仅作为 :class:`~.Item` 的基类，不作为直接创建使用
    """

    def __init__(self):
        self._init_rel_handle()

    def _init_rel_handle(self) -> None:
        self._rel_handle = _items_relation_registry.create(self)
        self._parents_changed_hooks: list[Callable] = []
        self._children_changed_hooks: list[Callable] = []

    def _parents_changed(self) -> None:
        for hook in self._parents_changed_hooks:
            hook()

    def _children_changed(self) -> None:
        for hook in self._children_changed_hooks:
            hook()

    @property
    def parents(self) -> list[RelT]:
        """
        父物件列表的一份拷贝
        """
        return self._rel_handle.parents_ref().copy()

    @property
    def children(self) -> list[RelT]:
        """
        子物件列表的一份拷贝
        """
        return self._rel_handle.children_ref().copy()

    def __iter__(self) -> Iterator[RelT]:
        return iter(self._rel_handle.children_ref())

    def __getitem__(self, i: SupportsIndex | slice):
        return self._rel_handle.children_ref()[i]

    def __contains__(self, obj: RelT) -> bool:
        return obj in self._rel_handle.children_ref()

    def __len__(self) -> int:
        return len(self._rel_handle.children_ref())

    def has_child(self) -> bool:
        return len(self._rel_handle.children_ref()) != 0

    def index(self, obj: RelT) -> int:
        """
        获取子物件在列表中的索引位置

        :param obj: 要查找的子物件
        :return: 子物件的索引位置
        :raises ValueError: 子物件不在列表中
        """
        return self._rel_handle.children_ref().index(obj)

    # region relation management

    @staticmethod
    def _get_handles(objs: Iterable[ItemRelation]) -> list[relation.RelationHandle]:
        try:
            return [obj._rel_handle for obj in objs]
        except AttributeError as e:
            raise RelationError(
                _('{obj} is not an `Item`, cannot be used as item children').format(e.obj)
            )

    def add(
        self,
        *objs: RelT,
        prepend: bool = False,
    ) -> Self:
        """
        向该物件添加子物件

        :param objs: 要添加的子物件
        :param prepend: 默认为 ``False``，如果为 ``True``，那么插入到子物件列表的开头
        """
        self._rel_handle.add(self._get_handles(objs), prepend)
        return self

    def insert(self, index: int, *objs: RelT) -> Self:
        """
        在指定索引位置插入子物件

        :param index: 插入位置的索引
        :param objs: 要插入的子物件
        """
        self._rel_handle.insert(index, self._get_handles(objs))
        return self

    def remove(self, *objs: RelT) -> Self:
        """
        从该物件移除子物件

        :param objs: 要移除的子物件
        """
        self._rel_handle.remove(self._get_handles(objs))
        return self

    def shuffle(self) -> Self:
        """
        随机打乱子物件的顺序

        .. note::

            该方法使用 :func:`random.shuffle` 进行随机打乱

            如果需要可重复的随机结果，请在调用此方法前使用 :func:`random.seed` 设置随机数种子
        """
        random.shuffle(self._rel_handle.children_ref())
        self._rel_handle.emit_children_changed()
        return self

    def clear_parents(self) -> Self:
        """
        清空父物件
        """
        self._rel_handle.clear_parents()
        return self

    def clear_children(self) -> Self:
        """
        清空子物件
        """
        self._rel_handle.clear_children()
        return self

    def ancestors(self, unordered: bool = False) -> list[RelT]:
        """
        获得祖先物件列表

        注：该方法会临时从 :meth:`walk_ancestors` 构造列表，对于遍历的需求，建议参考并使用 :meth:`walk_ancestors`

        :param unordered: 默认按照 DFS 顺序，若指定 ``unordered=True`` 则不保证顺序，对于复杂结构的性能会更佳
        """
        return list(self._walk_ancestors(unordered))

    def descendants(self, unordered: bool = False) -> list[RelT]:
        """
        获得后代物件列表

        注：该方法会临时从 :meth:`walk_descendants` 构造列表，对于遍历的需求，建议参考并使用 :meth:`walk_descendants`

        :param unordered: 默认按照 DFS 顺序，若指定 ``unordered=True`` 则不保证顺序，对于复杂结构的性能会更佳
        """
        return list(self._walk_descendants(unordered))

    # endregion

    # region `walk_` methods

    @overload
    def walk_ancestors(
        self, base_cls: None = None, *, unordered: bool = False
    ) -> Iterable[RelT]: ...
    @overload
    def walk_ancestors[Filter](
        self, base_cls: type[Filter], *, unordered: bool = False
    ) -> Iterable[Filter]: ...

    def walk_ancestors[Filter](
        self, base_cls: type[Filter] | None = None, *, unordered: bool = False
    ) -> Iterable[RelT | Filter]:
        """
        遍历祖先节点中以 ``base_cls`` 为基类的物件

        :param base_cls: 用于检查的基类，若缺省则遍历全部
        :param unordered: 默认按照 DFS 顺序，若指定 ``unordered=True`` 则不保证顺序，对于复杂结构的性能会更佳
        """
        yield from self._filter(base_cls, self._walk_ancestors(unordered))

    @overload
    def walk_descendants(
        self, base_cls: None = None, *, unordered: bool = False
    ) -> Iterable[RelT]: ...
    @overload
    def walk_descendants[Filter](
        self, base_cls: type[Filter], *, unordered: bool = False
    ) -> Iterable[Filter]: ...

    def walk_descendants[Filter](
        self, base_cls: type[Filter] | None = None, *, unordered: bool = False
    ) -> Iterable[RelT | Filter]:
        """
        遍历后代节点中以 ``base_cls`` 为基类的物件

        :param base_cls: 用于检查的基类，若缺省则遍历全部
        :param unordered: 默认按照 DFS 顺序，若指定 ``unordered=True`` 则不保证顺序，对于复杂结构的性能会更佳
        """
        yield from self._filter(base_cls, self._walk_descendants(unordered))

    @overload
    def walk_self_and_ancestors(
        self, root_only: bool = False, base_cls: None = None, *, unordered: bool = False
    ) -> Iterable[Self | RelT]: ...
    @overload
    def walk_self_and_ancestors[Filter](
        self, root_only: bool = False, base_cls: type[Filter] = object, *, unordered: bool = False
    ) -> Iterable[Filter]: ...

    def walk_self_and_ancestors[Filter](
        self,
        root_only: bool = False,
        base_cls: type[Filter] | None = None,
        *,
        unordered: bool = False,
    ) -> Iterable[Self | RelT | Filter]:
        """
        遍历自己以及后代节点中以 ``base_cls`` 为基类的物件

        :param root_only: 是否忽略所有祖先节点，仅考虑根节点
        :param base_cls: 用于检查的基类，若缺省则遍历全部
        :param unordered: 默认按照 DFS 顺序，若指定 ``unordered=True`` 则不保证顺序，对于复杂结构的性能会更佳
        """
        if root_only:
            if self._filter_self(base_cls):
                yield self
            return
        yield from self._filter(base_cls, self._chain_self_with(self._walk_ancestors(unordered)))

    @overload
    def walk_self_and_descendants(
        self, root_only: bool = False, base_cls: None = None, *, unordered: bool = False
    ) -> Iterable[Self | RelT]: ...
    @overload
    def walk_self_and_descendants[Filter](
        self, root_only: bool = False, base_cls: type[Filter] = object, *, unordered: bool = False
    ) -> Iterable[Filter]: ...

    def walk_self_and_descendants[Filter](
        self,
        root_only: bool = False,
        base_cls: type[Filter] | None = None,
        *,
        unordered: bool = False,
    ) -> Iterable[Self | RelT | Filter]:
        """
        遍历自己以及后代节点中以 ``base_cls`` 为基类的物件

        :param root_only: 是否忽略所有后代节点，仅考虑根节点
        :param base_cls: 用于检查的基类，若缺省则遍历全部
        :param unordered: 默认按照 DFS 顺序，若指定 ``unordered=True`` 则不保证顺序，对于复杂结构的性能会更佳
        """
        if root_only:
            if self._filter_self(base_cls):
                yield self
            return
        yield from self._filter(base_cls, self._chain_self_with(self._walk_descendants(unordered)))

    def walk_nearest_ancestors[Filter](self, base_cls: type[Filter]) -> Iterable[Filter]:
        """
        遍历祖先节点中以 ``base_cls`` 为基类的物件，但是排除已经满足条件的物件的祖先物件
        """
        yield from self._walk_nearest_family(
            base_cls, lambda rel: rel._rel_handle.walk_ancestor_dfs()
        )

    def walk_nearest_descendants[Filter](self, base_cls: type[Filter]) -> Iterable[Filter]:
        """
        遍历后代节点中以 ``base_cls`` 为基类的物件，但是排除已经满足条件的物件的后代物件
        """
        yield from self._walk_nearest_family(
            base_cls, lambda rel: rel._rel_handle.walk_descendant_dfs()
        )

    # endregion

    # region helper functions for `walk_` methods

    def _walk_ancestors(self, unordered: bool) -> Iterable[Any]:
        return (
            self._rel_handle.walk_ancestor_set()
            if unordered
            else self._rel_handle.walk_ancestor_dfs()
        )

    def _walk_descendants(self, unordered: bool) -> Iterable[Any]:
        return (
            self._rel_handle.walk_descendant_set()
            if unordered
            else self._rel_handle.walk_descendant_dfs()
        )

    @staticmethod
    def _filter(base_cls: type | None, lst: Iterable):
        if base_cls is None:
            yield from lst
            return

        for obj in lst:
            if isinstance(obj, base_cls):
                yield obj

    def _chain_self_with(self, lst: Iterable):
        yield self
        yield from lst

    def _filter_self(self, base_cls: type | None) -> bool:
        return base_cls is None or isinstance(self, base_cls)

    def _walk_nearest_family[Filter](
        self: ItemRelation,
        base_cls: type[Filter],
        fn_family: Callable[[ItemRelation | Any], Iterable[Any]],
    ) -> Generator[Filter, None, None]:

        lst = list(fn_family(self))

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

    # endregion
