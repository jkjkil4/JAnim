from __future__ import annotations

import math
from typing import Iterable, Self

import numpy as np

from janim.components.component import CmptGroup, CmptInfo
from janim.components.glow import Cmpt_Glow
from janim.components.points import Cmpt_Points
from janim.components.radius import Cmpt_Radius
from janim.components.rgbas import Cmpt_Rgbas, apart_alpha
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import PI
from janim.items.item import Item, mockable
from janim.items.points import Points
from janim.render.impl import VItemRenderer
from janim.typing import Alpha, AlphaArray, ColorArray, JAnimColor, Vect
from janim.utils.data import AlignedData
from janim.utils.simple_functions import clip

DEFAULT_STROKE_RADIUS = 0.02


class VItem(Points):
    '''
    贝塞尔曲线拼接物件，具体说明请参考 :class:`~.Cmpt_VPoints` 的文档
    '''
    points = CmptInfo(Cmpt_VPoints[Self])
    radius = CmptInfo(Cmpt_Radius[Self], DEFAULT_STROKE_RADIUS)

    stroke = CmptInfo(Cmpt_Rgbas[Self])
    fill = CmptInfo(Cmpt_Rgbas[Self])
    glow = CmptInfo(Cmpt_Glow[Self])

    color = CmptGroup(stroke, fill)

    renderer_cls = VItemRenderer

    def __init__(self, *points: Vect, fill_alpha=0, **kwargs):
        self.stroke_background = False
        super().__init__(*points, fill_alpha=fill_alpha, **kwargs)

        def reverse():
            for cmpt in (self.radius, self.stroke, self.fill):
                cmpt.reverse()

        Cmpt_Points.reverse.connect(self.points, reverse)

    def apply_style(
        self,
        stroke_radius: float | Iterable[float] | None = None,
        stroke_color: JAnimColor | ColorArray | None = None,
        stroke_alpha: Alpha | AlphaArray | None = None,
        stroke_background: bool | None = None,
        fill_color: JAnimColor | ColorArray | None = None,
        fill_alpha: Alpha | AlphaArray | None = None,
        color: JAnimColor | ColorArray | None = None,
        alpha: Alpha | AlphaArray | None = None,
        glow_color: JAnimColor | None = None,
        glow_alpha: Alpha | None = None,
        glow_size: float | None = None,
        **kwargs
    ) -> Self:
        if stroke_color is None:
            stroke_color = color
        if stroke_alpha is None:
            stroke_alpha = alpha

        if fill_color is None:
            fill_color = color
        if fill_alpha is None:
            fill_alpha = alpha

        if stroke_background is not None:
            self.stroke_background = stroke_background
        if stroke_radius is not None:
            self.radius.set(stroke_radius, root_only=True)
        self.stroke.set(stroke_color, stroke_alpha, root_only=True)
        self.fill.set(fill_color, fill_alpha, root_only=True)
        self.glow.set(glow_color, glow_alpha, glow_size, root_only=True)

        return super().apply_style(**kwargs)

    @mockable
    def set_stroke_background(self: Item, flag: bool = True, *, root_only: bool = False) -> Self:
        '''
        调整描边与填充的绘制顺序

        ``flag=True`` 会使得描边被填充遮盖，``flag=False`` 则会使得填充被描边遮盖
        '''
        for item in self.walk_self_and_descendants(root_only):
            if isinstance(item, VItem):
                item.stroke_background = flag
        return self

    def add_tip(
        self,
        alpha: float = 1.0,
        reverse: bool = False,
        colorize: bool = True,
        angle: float | None = None,
        fill_color: JAnimColor | None = None,
        stroke_color: JAnimColor | None = None,
        d_alpha: float = 1e-6,
        **tip_kwargs
    ):
        '''
        在 ``alpha`` 处创建一个箭头

        - 默认情况下，箭头与路径方向同向；若传入 ``reverse=True`` 则反向
        - 若传入 ``colorize=True`` （默认），则会使箭头的颜色与路径的颜色相同
        - 其余参数请参考 :class:`~.ArrowTip`
        '''
        if alpha >= 1.0:
            pos = self.points.get_end()
            angle_vert = self.points.end_direction
        elif alpha <= 0.0:
            pos = self.points.get_start()
            angle_vert = self.points.start_direction
        else:
            pos = self.points.pfp(alpha)
            angle_vert = self.points.pfp(clip(alpha + d_alpha, 0, 1)) - self.points.pfp(clip(alpha - d_alpha, 0, 1))

        if angle is None:
            angle = math.atan2(angle_vert[1], angle_vert[0])
        if reverse:
            angle += PI

        if colorize:
            if fill_color is None:
                fill_color = self.fill.get()[0][:3]
            if stroke_color is None:
                stroke_color = self.stroke.get()[0][:3]

        from janim.items.geometry.arrow import ArrowTip
        tip = ArrowTip(angle=angle, fill_color=fill_color, stroke_color=stroke_color, **tip_kwargs)
        tip.move_anchor_to(pos)
        self.add(tip)

        return tip

    @classmethod
    def align_for_interpolate(cls, item1: VItem, item2: VItem) -> AlignedData[Self]:
        subpaths1_count = len(item1.points.get_subpath_end_indices())
        subpaths2_count = len(item2.points.get_subpath_end_indices())

        aligned = super().align_for_interpolate(item1, item2)

        count = (aligned.data1.points.count() + 1) // 2
        for cmpt_name, array_name in (
            ('stroke', '_rgbas'),
            ('fill', '_rgbas'),
            ('radius', '_radii'),
        ):
            cmpt1 = aligned.data1.components[cmpt_name]
            cmpt2 = aligned.data2.components[cmpt_name]
            if cmpt1.not_changed(cmpt2):
                cmpt1.resize(count)
                # 使用这种方式保持 not_changed 的判断，以优化性能
                setattr(cmpt2, array_name, getattr(cmpt1, array_name).copy())
            else:
                cmpt1.resize(count)
                cmpt2.resize(count)

        if subpaths1_count != subpaths2_count:
            diff = abs(subpaths1_count - subpaths2_count)
            item = aligned.data1 if subpaths1_count < subpaths2_count else aligned.data2
            indices = item.points.get_subpath_end_indices()

            left_end = indices[0] // 2
            right_start = indices[-1 - diff] // 2 + 1

            rgbas = item.stroke.get().copy()

            left = rgbas[:left_end + 1]
            right = rgbas[right_start:]

            alphas = np.array([apart_alpha(alpha, diff + 1) for alpha in left[:, 3]])
            left[:, 3] = alphas

            alphas = np.array([apart_alpha(alpha, diff + 1) for alpha in right[:, 3]])
            right[:, 3] = alphas

            item.stroke.set(rgbas)

        return aligned
