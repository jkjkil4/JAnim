from __future__ import annotations

from typing import Iterable, Self

import numpy as np

from janim.components.component import CmptInfo
from janim.components.glow import Cmpt_Glow
from janim.components.mark import Cmpt_Mark
from janim.components.points import Cmpt_Points
from janim.components.radius import Cmpt_Radius
from janim.components.rgbas import Cmpt_Rgbas, apart_alpha
from janim.items.item import Item
from janim.locale import get_translator
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


# 兼容旧导入路径：
# 允许 `from janim.items.points import Group/NamedGroupMixin/NamedGroup` 暂时继续可用，
# 并在访问时提示迁移到 `janim.items.group`
def __getattr__(name: str):
    if name in {'Group', 'NamedGroupMixin', 'NamedGroup'}:
        from janim.utils.deprecation import deprecated
        deprecated(
            f'janim.items.points.{name}',
            f'janim.items.group.{name}',
            remove=(4, 4)
        )
        from janim.items import group
        return getattr(group, name)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
