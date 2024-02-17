from __future__ import annotations

from typing import Self

import numpy as np

from janim.components.component import CmptInfo, CmptGroup
from janim.components.vpoints import Cmpt_VPoints
from janim.components.rgbas import Cmpt_Rgbas, apart_alpha
from janim.components.radius import Cmpt_Radius
from janim.items.points import Points
from janim.render.impl import VItemRenderer
from janim.utils.data import AlignedData


class VItem(Points):
    points = CmptInfo(Cmpt_VPoints[Self])
    radius = CmptInfo(Cmpt_Radius[Self], 0.02)

    stroke = CmptInfo(Cmpt_Rgbas[Self])
    fill = CmptInfo(Cmpt_Rgbas[Self])

    color = CmptGroup(stroke, fill)

    renderer_cls = VItemRenderer

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
