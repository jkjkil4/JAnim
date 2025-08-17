from __future__ import annotations

import math
from typing import Iterable, Literal, Self

import numpy as np

from janim.components.component import CmptGroup, CmptInfo
from janim.components.glow import Cmpt_Glow
from janim.components.points import Cmpt_Points
from janim.components.radius import Cmpt_Radius
from janim.components.rgbas import Cmpt_Rgbas, apart_alpha
from janim.components.vpoints import SCALE_STROKE_RADIUS_KEY, Cmpt_VPoints
from janim.constants import PI
from janim.items.item import Item, mockable
from janim.items.points import Group, Points
from janim.locale.i18n import get_local_strings
from janim.render.renderer_vitem import VItemRenderer
from janim.typing import Alpha, AlphaArray, ColorArray, JAnimColor, Vect
from janim.utils.bezier import (bezier, inverse_interpolate,
                                partial_quadratic_bezier_points)
from janim.utils.data import AlignedData
from janim.utils.simple_functions import clip
from janim.utils.space_ops import get_norm

_ = get_local_strings('vitem')

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

    def init_connect(self) -> None:
        super().init_connect()

        def reverse():
            for cmpt in (self.radius, self.stroke, self.fill):
                cmpt.reverse()

        Cmpt_Points.reverse.connect(self.points, reverse)

        Cmpt_Points.apply_points_fn.connect(
            self.points,
            lambda factor, root_only: self.radius.scale(factor, root_only=root_only),
            key=SCALE_STROKE_RADIUS_KEY
        )

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
        angle: float | None = None,
        colorize: bool = True,
        fill_color: JAnimColor | None = None,
        stroke_color: JAnimColor | None = None,
        color: JAnimColor | None = None,
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

        if fill_color is None and color is not None:
            fill_color = color
        if stroke_color is None and color is not None:
            stroke_color = color

        if colorize:
            if fill_color is None:
                fill_color = self.fill.get()[0, :3]
            if stroke_color is None:
                stroke_color = self.stroke.get()[0, :3]

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


class DashedVItem(VItem, Group[VItem]):
    '''
    创建传入的 ``vitem`` 的虚线化版本

    - ``num_dashes``: 虚线段的数量
    - ``dashed_ratio``: 虚线段的占比，剩下的占比即为空白段
    - ``dash_offset``: 将虚线段的起始点沿着路径偏移的比率，例如 ``1`` 表示偏移一个虚线段的长度
    - ``equal_lengths``: 虚线段的长度是否相等，取值为 ``'equal'``、``'approx'`` 或 ``'none'``
        - ``'equal'``: 虚线段长度几乎相等
        - ``'approx'``: 虚线段长度近似相等
        - ``'none'``: 虚线段将按照曲线的参数 t 均匀分布，一般来说长度不相等
    '''
    def __init__(
        self,
        vitem: VItem,
        num_dashes: int = 15,
        *,
        dashed_ratio: float = 0.5,
        dash_offset: float = 0,
        stroke_color: JAnimColor | ColorArray | None = None,
        stroke_alpha: Alpha | AlphaArray | None = None,
        stroke_radius: float | Iterable[float] | None = None,
        equal_lengths: Literal['equal', 'approx', 'none'] = 'approx',
        **kwargs,
    ):
        self.dashed_ratio = dashed_ratio
        self.num_dashes = num_dashes

        self.groups = [
            Group.from_iterable(self.get_dashed_list(
                subpath,
                num_dashes,
                dashed_ratio,
                dash_offset,
                equal_lengths,
            ))
            for subpath in vitem.points.get_subpaths()
        ]

        if stroke_color is None:
            stroke_color = vitem.stroke.get()[0, :3]
        if stroke_alpha is None:
            stroke_alpha = vitem.stroke.get()[0, 3]
        if stroke_radius is None:
            stroke_radius = vitem.radius.get()[0]

        super().__init__(
            *self.groups,
            stroke_color=stroke_color,
            stroke_alpha=stroke_alpha,
            stroke_radius=stroke_radius,
            **kwargs
        )

    @staticmethod
    def get_dashed_list(
        points: np.ndarray,
        num_dashes: int = 15,
        dashed_ratio: float = 0.5,
        dash_offset: float = 0,
        equal_lengths: bool = True,
    ) -> list[VItem]:
        '''将 ``points`` 所表示的路径分割，返回一个包含各虚线段的列表'''
        if num_dashes <= 0 or len(points) < 3:
            return []
        r = dashed_ratio
        n = num_dashes
        is_closed = np.isclose(points[0], points[-1]).all()

        # Assuming total length is 1
        dash_len = r / n
        if is_closed:
            void_len = (1 - r) / n
        else:
            void_len = 1 - r if n == 1 else (1 - r) / (n - 1)

        period = dash_len + void_len
        phase_shift = (dash_offset % 1) * period

        if is_closed:
            # closed curves have equal amount of dashes and voids
            pattern_len = 1
        else:
            # open curves start and end with a dash, so the whole dash pattern with the last void is longer
            pattern_len = 1 + void_len

        dash_starts = [((i * period + phase_shift) % pattern_len) for i in range(n)]
        dash_ends = [
            ((i * period + dash_len + phase_shift) % pattern_len) for i in range(n)
        ]

        # closed shapes can handle overflow at the 0-point
        # open shapes need special treatment for it
        if not is_closed:
            # due to phase shift being [0...1] range, always the last dash element needs attention for overflow
            # if an entire dash moves out of the shape end:
            if dash_ends[-1] > 1 and dash_starts[-1] > 1:
                # remove the last element since it is out-of-bounds
                dash_ends.pop()
                dash_starts.pop()
            elif dash_ends[-1] < dash_len:  # if it overflowed
                if (
                    dash_starts[-1] < 1
                ):  # if the beginning of the piece is still in range
                    dash_starts.append(0)
                    dash_ends.append(dash_ends[-1])
                    dash_ends[-2] = 1
                else:
                    dash_starts[-1] = 0
            elif dash_starts[-1] > (1 - dash_len):
                dash_ends[-1] = 1

        if equal_lengths == 'approx':
            # 参考 Cmpt_VPoints.curve_and_prop_of_partial_point
            partials: list[float] = [0]
            for tup in Cmpt_VPoints.get_bezier_tuples_from_points(points):
                if np.isnan(tup[1]).all():
                    arclen = 0
                else:
                    arclen = get_norm(tup[2] - tup[0])
                partials.append(partials[-1] + arclen)
            full = partials[-1]

            def get_curve_and_prop(alpha: float) -> tuple[int, float]:
                if alpha == 0:
                    return (0, 0.0)
                if full == 0:
                    return len(partials) - 2, 1.0
                index = next(
                    (i for i, x in enumerate(partials) if x >= full * alpha),
                    len(partials) - 1
                )
                residue = float(inverse_interpolate(
                    partials[index - 1] / full, partials[index] / full, alpha
                ))
                return index - 1, residue

            # 参考 Cmpt_VPoints.partial_points_reduced
            def get_subcurve(alpha1: float, alpha2: float) -> np.ndarray:
                lower_index, lower_residue = get_curve_and_prop(alpha1)
                upper_index, upper_residue = get_curve_and_prop(alpha2)
                i1 = 2 * lower_index
                i2 = 2 * lower_index + 3
                i3 = 2 * upper_index
                i4 = 2 * upper_index + 3

                if lower_index == upper_index:
                    tup = partial_quadratic_bezier_points(points[i1:i2], lower_residue, upper_residue)
                    return np.array(tup, dtype=points.dtype)

                low_tup = partial_quadratic_bezier_points(points[i1:i2], lower_residue, 1)
                high_tup = partial_quadratic_bezier_points(points[i3:i4], 0, upper_residue)
                return np.vstack([low_tup, points[i2 + 1: i3], high_tup[1:]])

            return [
                VItem(*get_subcurve(dash_start, dash_end))
                for dash_start, dash_end in zip(dash_starts, dash_ends)
            ]
        elif equal_lengths == 'equal':
            norms = np.array(0)
            sample_points = 10
            for tup in Cmpt_VPoints.get_bezier_tuples_from_points(points):
                # 参考 Cmpt_VPoints.get_nth_curve_length_pieces
                curve = bezier(tup)
                samples = np.array([curve(a) for a in np.linspace(0, 1, sample_points)])
                diffs = np.diff(samples, axis=0)
                norms = np.append(norms, np.linalg.norm(diffs, axis=1))
            # add up length-pieces in array form
            length_vals = np.cumsum(norms)
            ref_points = np.linspace(0, 1, length_vals.size)
            curve_length = length_vals[-1]
            return [
                VItem(
                    *Cmpt_VPoints.partial_points_reduced(
                        points,
                        np.interp(
                            dash_start * curve_length,
                            length_vals,
                            ref_points,
                        ),
                        np.interp(
                            dash_end * curve_length,
                            length_vals,
                            ref_points,
                        )
                    )
                )
                for dash_start, dash_end in zip(dash_starts, dash_ends)
            ]
        elif equal_lengths == 'none':
            return [
                VItem(*Cmpt_VPoints.partial_points_reduced(points, dash_start, dash_end))
                for dash_start, dash_end in zip(dash_starts, dash_ends)
            ]
        else:
            raise ValueError(
                _('Invalid value for equal_lengths: {equal_lengths}')
                .format(equal_lengths=equal_lengths)
            )
