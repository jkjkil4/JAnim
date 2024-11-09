from __future__ import annotations

from typing import Iterable, Self, overload

from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.components.radius import Cmpt_Radius
from janim.components.rgbas import Cmpt_Rgbas, apart_alpha
from janim.items.item import Item
from janim.render.impl import DotCloudRenderer
from janim.typing import ColorArray, JAnimColor, Vect
from janim.utils.data import AlignedData
from janim.utils.iterables import (resize_preserving_order,
                                   resize_preserving_order_indice_groups)


class Points(Item):
    '''
    点集

    纯数据物件，不参与渲染
    '''
    points = CmptInfo(Cmpt_Points[Self])

    def __init__(self, *points: Vect, **kwargs):
        super().__init__(**kwargs)

        if points:
            self.points.set(points)

    def is_null(self) -> bool:
        return not self.points.has()


class Group[T](Points):
    '''
    将物件组成一组
    '''
    def __init__(self, *objs: T, **kwargs):
        super().__init__(children=objs, **kwargs)

        self.children: list[T]

    @staticmethod
    def from_iterable[T](objs: Iterable[T], **kwargs) -> Group[T]:
        return Group(*objs, **kwargs)

    @overload
    def __getitem__(self, value: int) -> T: ...
    @overload
    def __getitem__(self, value: slice) -> Group[T]: ...
    @overload
    def __getitem__(self, key: Iterable[int]) -> Group[T]: ...
    @overload
    def __getitem__(self, key: Iterable[bool]) -> Group[T]: ...

    def __getitem__(self, value):   # pragma: no cover
        return super().__getitem__(value)

    def __iter__(self):
        return iter(self.children)


class DotCloud(Points):
    color = CmptInfo(Cmpt_Rgbas[Self])
    radius = CmptInfo(Cmpt_Radius[Self], 0.05)

    renderer_cls = DotCloudRenderer

    def __init__(
        self,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        Cmpt_Points.reverse.connect(self.points, lambda: self.radius.reverse())

        self.points.resize_func = resize_preserving_order

    def apply_style(
        self,
        color: JAnimColor | ColorArray | None = None,
        alpha: float | Iterable[float] | None = None,
        radius: float | Iterable[float] | None = None,
        **kwargs
    ) -> Self:
        self.color.set(color, alpha, root_only=True)
        if radius is not None:
            self.radius.set(radius, root_only=True)

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
