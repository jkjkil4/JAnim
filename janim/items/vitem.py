from __future__ import annotations

from typing import Self, Iterable

import numpy as np

from janim.components.component import CmptInfo, CmptGroup
from janim.components.vpoints import Cmpt_VPoints
from janim.components.rgbas import Cmpt_Rgbas, apart_alpha
from janim.components.radius import Cmpt_Radius
from janim.items.points import Points
from janim.render.impl import VItemRenderer
from janim.utils.data import AlignedData
from janim.typing import Vect, JAnimColor, ColorArray, Alpha, AlphaArray


class VItem(Points):
    '''
    贝塞尔曲线拼接物件，具体说明请参考 :class:`~.Cmpt_VPoints` 的文档
    '''
    points = CmptInfo(Cmpt_VPoints[Self])
    radius = CmptInfo(Cmpt_Radius[Self], 0.02)

    stroke = CmptInfo(Cmpt_Rgbas[Self])
    fill = CmptInfo(Cmpt_Rgbas[Self])

    color = CmptGroup(stroke, fill)

    renderer_cls = VItemRenderer

    def __init__(
        self,
        *points: Vect,
        stroke_radius: float | Iterable[float] | None = None,
        stroke_color: JAnimColor | ColorArray | None = None,
        stroke_alpha: Alpha | AlphaArray | None = None,
        fill_color: JAnimColor | ColorArray | None = None,
        fill_alpha: Alpha | AlphaArray | None = 0,
        color: JAnimColor | ColorArray | None = None,
        alpha: Alpha | AlphaArray | None = None,
        root_only: bool = False,
        **kwargs
    ):
        super().__init__(*points, **kwargs)
        if stroke_color is None:
            stroke_color = color
        if stroke_alpha is None:
            stroke_alpha = alpha

        if fill_color is None:
            fill_color = color
        if fill_alpha is None:
            fill_alpha = alpha

        if stroke_radius is not None:
            self.radius.set(stroke_radius, root_only=root_only)
        self.stroke.set(stroke_color, stroke_alpha, root_only=root_only)
        self.fill.set(fill_color, fill_alpha, root_only=root_only)

    class Data(Points.Data['VItem']):
        @classmethod
        def align_for_interpolate(cls, data1: VItem.Data, data2: VItem.Data) -> AlignedData[Self]:
            subpaths1_count = len(data1.cmpt.points.get_subpath_end_indices())
            subpaths2_count = len(data2.cmpt.points.get_subpath_end_indices())

            aligned = super().align_for_interpolate(data1, data2)

            for data in (aligned.data1, aligned.data2):
                count = (data.cmpt.points.count() - 1) // 2
                data.cmpt.color.resize(count)
                data.cmpt.radius.resize(count)

            if subpaths1_count != subpaths2_count:
                diff = abs(subpaths1_count - subpaths2_count)
                data = aligned.data1 if subpaths1_count < subpaths2_count else aligned.data2
                indices = data.cmpt.points.get_subpath_end_indices()

                left_end = indices[0] // 2
                right_start = indices[-1 - diff] // 2 + 1

                rgbas = data.cmpt.stroke.get()

                left = rgbas[:left_end + 1]
                right = rgbas[right_start:]

                alphas = np.array([apart_alpha(alpha, diff + 1) for alpha in left[:, 3]])
                left[:, 3] = alphas

                alphas = np.array([apart_alpha(alpha, diff + 1) for alpha in right[:, 3]])
                right[:, 3] = alphas

                data.cmpt.stroke.set(rgbas)

            return aligned
