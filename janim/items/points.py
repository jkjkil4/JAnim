from __future__ import annotations

from janim.items.item import Item
from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.components.rgbas import Cmpt_Rgbas
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

        self.points.set(points)


class DotCloud(Points):
    color = CmptInfo(Cmpt_Rgbas)

    renderer_cls = DotCloudRenderer

    class Data(Item.Data['DotCloud']):
        @classmethod
        def align_for_interpolate(
            cls,
            data1: DotCloud.Data,
            data2: DotCloud.Data
        ) -> AlignedData[DotCloud.Data]:
            aligned = super().align_for_interpolate(data1, data2)

            for data in (aligned.data1, aligned.data2):
                data.cmpt.color.resize(data.cmpt.points.count())

            return aligned
