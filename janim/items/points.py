from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Iterable, Self, TypeVar, overload

import numpy as np

from janim.components.component import CmptInfo
from janim.components.glow import Cmpt_Glow
from janim.components.mark import Cmpt_Mark
from janim.components.points import Cmpt_Points
from janim.components.radius import Cmpt_Radius
from janim.components.rgbas import Cmpt_Rgbas, apart_alpha
from janim.exception import GetItemError
from janim.items.item import Item
from janim.locale.i18n import get_translator
from janim.render.renderer_dotcloud import DotCloudRenderer
from janim.typing import Alpha, ColorArray, JAnimColor, Vect
from janim.utils.data import AlignedData
from janim.utils.iterables import (resize_preserving_order,
                                   resize_preserving_order_indice_groups)

_ = get_translator('janim.items.points')


class Points(Item):
    """
    点集

    纯数据物件，不参与渲染
    """
    points = CmptInfo(Cmpt_Points[Self])

    def __init__(self, *points: Vect, **kwargs):
        super().__init__(**kwargs)

        if points:
            self.points.set(points)

    def is_null(self) -> bool:
        return not self.points.has()

    @property
    def distance_sort_reference_point(self) -> np.ndarray | None:
        if not self._distance_sort:
            return None
        return self.points.self_box.center


class Point(Points):
    """
    一个点

    可以使用 ``.location`` 得到当前位置

    纯数据物件，不参与渲染；若想在画面中渲染点，可参考 :class:`~.Dot`
    """
    def __init__(self, location: Vect, **kwargs):
        super().__init__(location, **kwargs)

    @property
    def location(self) -> np.ndarray:
        return self.points.get_start()


class MarkedItem(Points):
    """
    带有标记点的物件

    例如 :class:`~.TextChar`、 :class:`~.TextLine`、 :class:`~.Arc` 和 :class:`~.RegularPolygon` 都以该类作为基类，
    使得可以

    - 通过 ``.mark.get(...)`` 的方式得到标记点位置，并会因为 ``points`` 的变化而同步更新
    - 通过 ``.mark.set(...)`` 的方式移动标记点位置，并让 ``points`` 同步移动

    自定义物件示例：

    .. code-block:: python

        class MarkedSquare(MarkedItem, Square):
            def __init__(self, side_length: float = 2.0, **kwargs) -> None:
                super().__init__(side_lenght, **kwargs)
                self.mark.set_points([RIGHT * side_length / 4])

    这段代码的 ``self.mark.set_points([RIGHT * side_length / 4])`` 设置了在 x 轴方向上 75% 处的一个标记点，
    这个标记点会自动跟踪物件的坐标变换，具体参考 :ref:`基本样例 <basic_examples>` 中的对应代码
    """

    mark = CmptInfo(Cmpt_Mark[Self])

    def __init__(self, *args, **kwargs):
        self._blocking_signals = False
        super().__init__(*args, **kwargs)

    def init_connect(self) -> None:
        super().init_connect()

        Cmpt_Points.apply_points_fn.connect(self.points, self._points_to_mark_slot)
        Cmpt_Mark.set.connect(self.mark, self._mark_to_points_slot)

    def _points_to_mark_slot(self, func, about_point) -> None:
        if self._blocking_signals:
            return
        self.mark.apply_points_fn(func, about_point)

    def _mark_to_points_slot(self, vector, root_only) -> None:
        self._blocking_signals = True
        self.points.shift(vector, root_only=root_only)
        self._blocking_signals = False


class DotCloud(Points):
    color = CmptInfo(Cmpt_Rgbas[Self])
    radius = CmptInfo(Cmpt_Radius[Self], 0.05)

    glow = CmptInfo(Cmpt_Glow[Self])

    renderer_cls = DotCloudRenderer

    def __init__(
        self,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.points.resize_func = resize_preserving_order

    def init_connect(self) -> None:
        super().init_connect()
        Cmpt_Points.reverse.connect(self.points, lambda: self.radius.reverse())

    def apply_style(
        self,
        color: JAnimColor | ColorArray | None = None,
        alpha: float | Iterable[float] | None = None,
        radius: float | Iterable[float] | None = None,
        glow_color: JAnimColor | None = None,
        glow_alpha: Alpha | None = None,
        glow_size: float | None = None,
        **kwargs
    ) -> Self:
        self.color.set(color, alpha, root_only=True)
        if radius is not None:
            self.radius.set(radius, root_only=True)
        self.glow.set(glow_color, glow_alpha, glow_size, root_only=True)

        return super().apply_style(**kwargs)

    @classmethod
    def align_for_interpolate(
        cls,
        item1: DotCloud,
        item2: DotCloud,
    ) -> AlignedData[DotCloud]:
        len1 = len(item1.points.get())
        len2 = len(item2.points.get())

        aligned = super().align_for_interpolate(item1, item2)

        for data in (aligned.data1, aligned.data2):
            points_count = data.points.count()
            data.color.resize(points_count)
            data.radius.resize(points_count)

        if len1 != len2:
            indice_groups = resize_preserving_order_indice_groups(min(len1, len2), max(len1, len2))

            cmpt_to_fade = aligned.data1.color if len1 < len2 else aligned.data2.color
            rgbas = cmpt_to_fade.get().copy()
            for group in indice_groups:
                rgbas[group, 3] = apart_alpha(rgbas[group[0], 3], len(group))
            cmpt_to_fade.set_rgbas(rgbas)

        return aligned


class GlowDot(DotCloud):
    def __init__(self, *args, glow_alpha=0.5, **kwargs):
        super().__init__(*args, glow_alpha=glow_alpha, **kwargs)


if TYPE_CHECKING:
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

    def __getitem__(self, value):   # pragma: no cover
        return super().__getitem__(value)

    def __iter__(self):
        return iter(self._children)


class NamedGroupMixin[T](Group[T]):
    """
    方便用于例如 :class:`~.Axes` 继承的基础类

    另见 :class:`NamedGroup`
    """
    def __init__(self, *items: T, named: dict[str, T], **kwargs):
        super().__init__(**kwargs)
        self._named_indices: dict[str, int] = {}
        self.add(*items, **named)

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
                key: idx + len(all_items)
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

        # 仿照删除物件的过程，更新 _named_indices
        for obj in items:
            # 被删除的一个物件的下标
            try:
                index = self.index(obj)
            except ValueError:
                continue

            # 更新 _named_indices：
            # 遍历，如果 index 命中，则删除这一项；如果是在 index 之后的，则减一
            remove: str | None = None
            for key, value in self._named_indices.items():
                if index == value:
                    assert remove is None
                    remove = key
                if index < value:
                    self._named_indices[key] = value - 1

            if remove is not None:
                del self._named_indices[remove]

        return super().remove(*items)

    def shuffle(self) -> Self:
        # 根据 key-下标 对应关系，得到打乱之前的 key-对象 对应关系
        named_objs = {
            key: self._children[index]
            for key, index in self._named_indices.items()
        }

        super().shuffle()

        # 计算新的 key-下标对应关系
        self._named_indices = {
            key: self.index(obj)
            for key, obj in named_objs.items()
        }
        return self

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
        return {
            key: self[value]
            for key, value in self._named_indices.items()
        }

    # region 对 stored 的相关处理，不是什么很重要的细节

    def store(self):
        copy_item = super().store()
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
