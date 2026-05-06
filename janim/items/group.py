from __future__ import annotations

import itertools as it
from typing import TYPE_CHECKING, Generic, Iterable, Self, TypeVar, overload

from janim.exception import GetItemError
from janim.items.item import Item
from janim.items.points import Points
from janim.locale import get_translator

_ = get_translator('janim.items.group')

if TYPE_CHECKING:  # 在支持更高级 typing 的同时保持对 3.12 的兼容
    T = TypeVar('T', default=Item)
else:
    T = TypeVar('T')


class Group(Points, Generic[T]):
    """
    物件组

    将物件组成一组
    """

    def __init__(self, *items: T, **kwargs):
        super().__init__(children=items, **kwargs)

        self._children: list[T]

    @staticmethod
    def from_iterable[T](items: Iterable[T], **kwargs) -> Group[T]:
        return Group(*items, **kwargs)

    @overload
    def __getitem__(self, key: int) -> T: ...
    @overload
    def __getitem__(self, key: slice | Iterable[int] | Iterable[bool]) -> Group[T]: ...

    def __getitem__(self, value):  # pragma: no cover
        return super().__getitem__(value)

    def __iter__(self):
        return iter(self._children)


class NamedGroupMixin[T](Group[T]):
    """
    方便用于例如 :class:`~.Axes` 继承的基础类

    另见 :class:`NamedGroup`
    """

    def __init__(self, *items: T, named: dict[str, T], **kwargs):
        super().__init__(*items, *named.values(), **kwargs)
        self._named_indices: dict[str, int] = {
            name: len(items) + i  #
            for i, name in enumerate(named)
        }
        # 相当于
        # super().__init__(**kwargs)
        # self._named_indices: dict[str, int] = {}
        # self.add(*items, **named)
        # 但是因为这样写是先传递 **kwargs 再 self.add，会导致 Item.set 因为没有子物件而忽略 kwargs 检查

    def add(self, *items: T, prepend=False, **named_items: T) -> Self:
        """
        向该物件添加子物件，并且可以通过具名参数设定具名子物件

        :param items: 要添加的子物件
        :param named_items: 要添加的具名子物件
        :param prepend: 默认为 ``False``，如果为 ``True``，那么插入到子物件列表的开头
        """
        all_items = items + tuple(named_items.values())

        # 添加物件
        super().add(*all_items, prepend=prepend)

        # 更新已有的索引
        if prepend:
            self._named_indices = {
                key: idx + len(all_items)  #
                for key, idx in self._named_indices.items()
            }

        # 建立新物件的索引
        if prepend:
            index_start = len(items)
        else:
            index_start = len(self._children) - len(named_items)

        # 新物件的索引为 [ index_start, index_start + len(named_items) )
        for i, name in enumerate(named_items.keys()):
            self._named_indices[name] = index_start + i

        return self

    def insert(self, index: int, *items: T, **named_items: T) -> Self:
        """
        在指定索引位置插入子物件，并且可以通过具名参数设定具名子物件

        :param index: 插入位置的索引
        :param items: 要插入的子物件
        :param named_items: 要插入的具名子物件
        """
        # 将可能的负下标转换为正下标，使得能正确更新 _named_indices
        # 例如 [a,b,c,d] 中 -1 应指向 len - 1 的 d，所以即为 len + index
        actual_index = index if index >= 0 else len(self._children) + index
        # 限制在 0 ~ len-1 之间，避免新索引计算错误
        actual_index = max(0, min(actual_index, len(self._children) - 1))

        all_items = items + tuple(named_items.values())

        # 插入物件
        super().insert(actual_index, *all_items)

        # 更新已有的索引
        self._named_indices = {
            key: idx + len(all_items) if idx >= actual_index else idx
            for key, idx in self._named_indices.items()
        }

        # 建立新物件的索引
        index_start = actual_index + len(items)

        # 新物件的索引为 [ index_start, index_start + len(named_items) )
        for i, name in enumerate(named_items.keys()):
            self._named_indices[name] = index_start + i

        return self

    def remove(self, *items_or_names: T | str) -> Self:
        """
        从该物件移除子物件

        :param items_or_names: 要移除的子物件或具名子物件的名称
        """
        items = [
            self.by_name(item_or_name) if isinstance(item_or_name, str) else item_or_name
            for item_or_name in items_or_names
        ]

        # 仿照删除物件的过程，更新 new_named_indices
        new_named_indices = self._named_indices.copy()

        for obj in items:
            # 被删除的一个物件的下标
            try:
                index = self.index(obj)
            except ValueError:
                continue

            # 更新 new_named_indices：
            # 遍历，如果 index 命中，则删除这一项；如果是在 index 之后的，则减一
            remove: str | None = None
            for key, value in self._named_indices.items():
                if index == value:
                    assert remove is None
                    remove = key
                if index < value:
                    new_named_indices[key] -= 1

            if remove is not None:
                del self._named_indices[remove]
                del new_named_indices[remove]

        self._named_indices = new_named_indices
        return super().remove(*items)

    def shuffle(self) -> Self:
        # 根据 key-下标 对应关系，得到打乱之前的 key-对象 对应关系
        named_objs = {
            key: self._children[index]  #
            for key, index in self._named_indices.items()
        }

        super().shuffle()

        # 计算新的 key-下标对应关系
        self._named_indices = {
            key: self.index(obj)  #
            for key, obj in named_objs.items()
        }
        return self

    def set_name(self, item: Item, name: str) -> Self:
        """
        设置一个已有的子物件的对应名称

        :param item: 一个已有的子物件
        :param name: 要设置的名称
        """
        index = self.index(item)
        # 删除 _named_indices 中原先记录的 ? -> index
        for key, value in self._named_indices.items():
            if value == index:
                del self._named_indices[key]
                break  # 可以假设只存在一个，所以 break
        self._named_indices[name] = index

    @overload
    def __getitem__(self, key: str) -> T: ...
    @overload
    def __getitem__(self, key: int) -> T: ...
    @overload
    def __getitem__(self, key: slice | Iterable[int] | Iterable[bool]) -> Group[T]: ...

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.by_name(key)

        return super().__getitem__(key)

    def by_name(self, key: str) -> T:
        """
        根据名称获取子物件
        """
        index = self._named_indices.get(key, None)
        if index is None:
            raise GetItemError(_('Cannot find item with named key "{key}"').format(key=key))

        return self[index]

    def resolve(self) -> dict[str, T]:
        """
        将具名子物件的内部索引关系整体解析为到物件的映射

        :return: 名称到子物件的映射字典
        """
        return {key: self[value] for key, value in self._named_indices.items()}

    def _index_names(self) -> dict[int, str]:
        """
        具名子物件的下标到名称的对应关系，即 ``_named_indices`` 的反向字典
        """
        return {index: name for name, index in self._named_indices.items()}

    def children_with_name(self) -> list[tuple[T, str | None]]:
        """
        返回的列表中与子物件列表相似，但是每个元素是一个包含 ``(单个子物件, 其对应的名称)`` 的元组，如果不是具名子物件则名称为 ``None``
        """
        index_names = self._index_names()
        return [
            (item, index_names.get(i, None))  #
            for i, item in enumerate(self._children)
        ]

    # region 对 stored 的相关处理，不是什么很重要的细节

    def store(self, **kwargs):
        copy_item = super().store(**kwargs)
        copy_item._named_indices = {}
        copy_item._stored_named_indices = self.get_named_indices().copy()
        return copy_item

    def restore(self, other: NamedGroupMixin) -> Self:
        assert isinstance(other, NamedGroupMixin)
        if self._stored:
            self._stored_named_indices = other.get_named_indices().copy()
        return super().restore(other)

    def _unstore(self, child_restorer) -> None:
        super()._unstore(child_restorer)
        self._named_indices = self._stored_named_indices.copy()

    def get_named_indices(self) -> dict[str, int]:
        return self._stored_named_indices if self._stored else self._named_indices

    # endregion

    # region 对子物件 copy 和 become 的处理

    def copy(self, *, root_only: bool = False):
        copy_item = super().copy(root_only=root_only)
        if root_only:
            copy_item._named_indices = {}
        else:
            copy_item._named_indices = self._named_indices.copy()
        return copy_item

    def _children_become(self, other: Item, auto_visible: bool) -> None:
        # 如果 other 不是具名物件组则按普通方式处理
        if not isinstance(other, NamedGroupMixin):
            super()._children_become(other, auto_visible)
            return

        self_children = self.children_with_name()
        target_children = other.children_with_name()
        common_names = self._named_indices.keys() & other._named_indices.keys()

        def is_common(name: str | None) -> bool:
            return name is not None and name in common_names

        # 清空自身原有的 children
        self.clear_children()

        # 遍历 other 的子物件，依次在 self_children 中寻找来源物件
        # 对于 other 的每个子物件：
        # (1) 如果是共有的具名子物件，则在 self 中找到对应的具名子物件
        # (2) 如果不是共有的具名子物件，则寻找 self 中的第一个不是共有的具名子物件
        src_children: list[Item | None] = []
        for _, target_name in target_children:
            # 如果 other_children 空了则直接停止寻找来源物件
            if not self_children:
                break

            # 寻找来源物件
            is_target_name_common = is_common(target_name)
            src_idx = None
            for i, (_, self_name) in enumerate(self_children):
                if is_target_name_common:
                    # (1)
                    if self_name == target_name:
                        src_idx = i
                        break
                else:
                    # (2)
                    if not is_common(self_name):
                        src_idx = i
                        break

            # 如果 source_idx 非 None，则从 self_children 中 pop
            if src_idx is not None:
                src_item = self_children.pop(src_idx)[0]
            else:
                src_item = None

            src_children.append(src_item)

        # 辅助函数
        def add(item: Item, name: str | None) -> None:
            if name is None:
                self.add(item)
            else:
                self.add(**{name: item})

        # 根据配对结果处理子物件
        # 处理逻辑和普通方式会有点像
        for src, target in it.zip_longest(src_children, target_children):
            assert target is not None
            target_item, target_name = target

            if src is None or type(src) is not type(target_item):
                add(target_item, target_name)
            else:
                add(src.become(target_item), target_name)

    # endregion


class NamedGroup[T](NamedGroupMixin[T]):
    """
    具名物件组，可以使用类似 ``group['name']`` 的形式来获取其中的具名物件

    :param items: 初始物件
    :param named_items: 初始具名物件

    也可以使用 :meth:`~.NamedGroupMixin.add` 或 :meth:`~.NamedGroupMixin.insert` 方法，传入具名参数来新增具名子物件

    示例：

    .. code-block:: python

        group = NamedGroup(
            text=Text('lorem'),
            shape=Circle()
        )
        group.points.arrange(DOWN, aligned_edge=LEFT)

        self.play(
            group['text'].anim.color.set(GREEN),
            group['shape'].anim.color.set(YELLOW),
            lag_ratio=0.5
        )

        def updater(group: NamedGroup, p: UpdaterParams) -> None:
            group.points.rotate(TAU * p.alpha)
            group['text'].color.mix(BLUE, p.alpha)

        self.play(
            GroupUpdater(group, updater)
        )

    .. note::

        无法像 :class:`Group` 那样使用初始化参数

        .. code-block:: python

            group = Group(..., color=RED)

        为了解决这一问题，你可以写为

        .. code-block:: python

            group = NamedGroup(...)
            group.set(color=RED)

    .. note::

        如果你想要将 :class:`NamedGroup` 作为父类并继承，使用 :class:`NamedGroupMixin` 会是更好的选择

        因为它不会将所有 ``**kwargs`` 都吃掉，而是使用显式的 ``named`` 参数来指定具名子物件字典
    """

    def __init__(self, *items: T, **named_items: T):
        super().__init__(*items, named=named_items)
