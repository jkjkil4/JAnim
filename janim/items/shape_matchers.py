from __future__ import annotations

import janim.items.boolean_ops as boolean_ops
from janim.camera.camera import Camera
from janim.constants import DOWN, LEFT, RIGHT, SMALL_BUFF, UP, YELLOW
from janim.items.geometry.line import Line
from janim.items.geometry.polygon import Rect
from janim.items.points import Points
from janim.typing import JAnimColor
from janim.utils.config import Config
from janim.utils.data import Align, Margins, MarginsType
from janim.utils.deprecation import deprecated_classvar
from janim.utils.dict_ops import merge_dicts_recursively


class SurroundingRect(Rect):
    """
    包围矩形框
    """
    def __init__(
        self,
        item: Points,
        *,
        buff: MarginsType = SMALL_BUFF,
        color: JAnimColor = YELLOW,
        width: float | None = None,
        height: float | None = None,
        align: Align = Align.Center,
        **kwargs
    ):
        box = item.points.box

        if not isinstance(buff, Margins):
            buff = Margins(buff)
        if width is None:
            width = box.width + buff.left + buff.right
        if height is None:
            height = box.height + buff.top + buff.bottom

        super().__init__(width, height, color=color, **kwargs)

        if align & Align.Left:
            x = box.get_x(LEFT) - buff.left + width / 2
        elif align & Align.Right:
            x = box.get_x(RIGHT) + buff.right - width / 2
        else:
            x = box.get_x() + (buff.right - buff.left) / 2

        if align & Align.Bottom:
            y = box.get_y(DOWN) - buff.bottom + height / 2
        elif align & Align.Top:
            y = box.get_y(UP) + buff.top - height / 2
        else:
            y = box.get_y() + (buff.top - buff.bottom) / 2

        self.points.move_to([x, y, box.get_z()])


class FrameRect(Rect):
    """
    覆盖整个画面的矩形

    - 可以传入 ``camera`` 指定以其画面区域为准
    - 若不传入则产生默认宽高 ``frame_width`` 和 ``frame_height`` 的矩形
    """
    def __init__(self, camera: Camera | None = None, **kwargs):
        if camera is None:
            super().__init__(Config.get.frame_width, Config.get.frame_height, **kwargs)
        else:
            super().__init__(1, 1, **kwargs)
            info = camera.points.info
            hvect_half = info.horizontal_vect / 2
            vvect_half = info.vertical_vect / 2
            center = info.center
            self.points.set_as_corners([
                center + hvect_half + vvect_half,
                center - hvect_half + vvect_half,
                center - hvect_half - vvect_half,
                center + hvect_half - vvect_half,
                center + hvect_half + vvect_half
            ])


class HighlightRect(boolean_ops.Difference):
    """
    高亮区域，即 :class:`FrameRect` 挖去 :class:`SurroundingRect`
    """

    difference_config_d = deprecated_classvar(
        Rect.preset_shadow,
        'HighlightRect.difference_config_d',
        'Rect.preset_shadow',
        remove=(4, 3)
    )

    def __init__(
        self,
        # SurroundingRect
        item: Points,

        # FrameRect
        camera: Camera | None = None,
        *,
        # SurroundingRect
        buff: MarginsType = SMALL_BUFF,
        width: float | None = None,
        height: float | None = None,
        align: Align = Align.Center,

        # Difference
        **kwargs
    ):
        kwargs = merge_dicts_recursively(Rect.preset_shadow, kwargs)
        super().__init__(
            FrameRect(camera),
            SurroundingRect(item, buff=buff, width=width, height=height, align=align),
            **kwargs
        )


class Underline(Line):
    def __init__(self, item: Points, *, buff: float = SMALL_BUFF, **kwargs):
        super().__init__(LEFT, RIGHT, **kwargs)
        self.points.set_width(item.points.box.width)
        self.points.next_to(item, DOWN, buff=buff)
