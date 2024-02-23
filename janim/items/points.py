from __future__ import annotations

from typing import Iterable, Self

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

    def set_style(
        self,
        color: JAnimColor | ColorArray | None = None,
        alpha: float | Iterable[float] | None = None,
        radius: float | Iterable[float] | None = None,
        **kwargs
    ) -> None:
        self.color.set(color, alpha)
        if radius is not None:
            self.radius.set(radius)

        super().set_style(**kwargs)

    class Data(Item.Data['DotCloud']):
        @classmethod
        def align_for_interpolate(
            cls,
            data1: DotCloud.Data,
            data2: DotCloud.Data,
        ) -> AlignedData[DotCloud.Data]:
            len1 = len(data1.cmpt.points.get())
            len2 = len(data2.cmpt.points.get())

            aligned = super().align_for_interpolate(data1, data2)

            for data in (aligned.data1, aligned.data2):
                points_count = data.cmpt.points.count()
                data.cmpt.color.resize(points_count)
                data.cmpt.radius.resize(points_count)

            if len1 != len2:
                indice_groups = resize_preserving_order_indice_groups(min(len1, len2), max(len1, len2))

                cmpt_to_fade = aligned.data1.cmpt.color if len1 < len2 else aligned.data2.cmpt.color
                rgbas = cmpt_to_fade.get()
                for group in indice_groups:
                    rgbas[group, 3] = apart_alpha(rgbas[group[0], 3], len(group))
                cmpt_to_fade.set_rgbas(rgbas)

            return aligned
