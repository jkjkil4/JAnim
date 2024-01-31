from __future__ import annotations

from typing import Iterable

from janim.items.item import Item
from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.components.rgbas import Cmpt_Rgbas
from janim.components.radius import Cmpt_Radius
from janim.typing import Vect
from janim.utils.data import AlignedData
from janim.render.impl import DotCloudRenderer


class Points(Item):
    '''
    点集

    纯数据物件，不参与渲染
    '''
    points = CmptInfo(Cmpt_Points)

    def __init__(self, *points: Vect, **kwargs):
        super().__init__(**kwargs)

        if points:
            self.points.set(points)


class DotCloud(Points):
    color = CmptInfo(Cmpt_Rgbas)
    radius = CmptInfo(Cmpt_Radius)

    renderer_cls = DotCloudRenderer

    def __init__(self, *args, radius: float | Iterable[float] | None = None, **kwargs):
        super().__init__(*args, **kwargs)

        if radius is not None:
            self.radius.set(radius)

    class Data(Item.Data['DotCloud']):
        @classmethod
        def align_for_interpolate(
            cls,
            data1: DotCloud.Data,
            data2: DotCloud.Data
        ) -> AlignedData[DotCloud.Data]:
            aligned = super().align_for_interpolate(data1, data2)

            for data in (aligned.data1, aligned.data2):
                points_count = data.cmpt.points.count()
                data.cmpt.color.resize(points_count)
                data.cmpt.radius.resize(points_count)

            return aligned
