from dataclasses import dataclass
from typing import Iterable, overload

import numpy as np

from janim.anims_core.time import TimeRange
from janim.constants import BLACK, DOWN, SMALL_BUFF, UP
from janim.items.group import Group
from janim.items.shape_matchers import SurroundingRect
from janim.items.svg.typst import TypstText
from janim.items.text import Text
from janim.timeline.core import TimelineCore
from janim.typing import JAnimColor
from janim.utils.config import Config
from janim.utils.iterables import resize_preserving_order


@dataclass
class SubtitleInfo:
    """
    调用 :meth:`~.Timeline.subtitle` 的参数信息
    """

    text: str
    range: TimeRange
    kwargs: dict
    subtitle: Text | TypstText


class SubtitlesMixin(TimelineCore):
    """
    向 :class:`~.Timeline`  提供添加字幕的功能

    .. hint::

        该类中的方法都可以直接在 :class:`~.Timeline` 中使用
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.subtitle_infos: list[SubtitleInfo] = []

    @overload
    def subtitle(
        self,
        text: str | Iterable[str],
        duration: float = 1,
        *,
        delay: float = 0,
        scale: float | Iterable[float] = 0.8,
        use_typst_text: bool | Iterable[bool] = False,
        #
        surrounding_color: JAnimColor = BLACK,
        surrounding_alpha: float = 0.5,
        #
        font: str | Iterable[str] = [],
        #
        depth: float = -1e5,
        **kwargs,
    ) -> TimeRange: ...

    @overload
    def subtitle(self, text: str | Iterable[str], range: TimeRange, **kwargs) -> TimeRange: ...

    def subtitle(
        self,
        text: str | Iterable[str],
        duration: float = 1,
        *,
        delay: float = 0,
        scale: float | Iterable[float] = 1,
        base_scale: float = 0.8,
        use_typst_text: bool | Iterable[bool] = False,
        #
        surrounding_color: JAnimColor = BLACK,
        surrounding_alpha: float = 0.5,
        #
        font: str | Iterable[str] = [],
        #
        depth: float = -1e5,
        **kwargs,
    ) -> TimeRange:
        """
        添加字幕

        - 文字可以传入一个列表，纵向排列显示
        - 可以指定在当前位置往后 ``delay`` 秒才显示
        - ``duration`` 表示持续时间
        - ``scale`` 表示对文字的缩放，可以传入列表表示对各个文字的缩放
        - ``use_typst_text`` 表示是否使用 :class:`TypstText`，可以传入列表表示各个文字是否使用
        - 将 ``surrounding_alpha`` 设置为 ``0`` 可以禁用附带的底框

        :class:`~.Config` 中也提供了一些可以配置的参数：

        - ``subtitle_font`` 可全局配置字幕所使用的字体
        - ``subtitle_to_edge_buff`` 可配置字幕离底边的距离，默认是 ``DEFAULT_ITEM_TO_EDGE_BUFF``

        返回值表示显示的时间段
        """
        # 处理参数
        text_lst = [text] if isinstance(text, str) else text
        scale_lst = [scale] if not isinstance(scale, Iterable) else scale
        use_typst_lst = (
            [use_typst_text] if not isinstance(use_typst_text, Iterable) else use_typst_text
        )

        if isinstance(duration, TimeRange):
            range = duration
        else:
            at = self.current_time + delay
            range = TimeRange(at, at + duration)

        # 处理字体
        cfg_font = Config.get.subtitle_font
        if cfg_font:
            if isinstance(font, str):
                font = [font]
            else:
                font = list(font)

            if isinstance(cfg_font, str):
                font.append(cfg_font)
            else:
                font.extend(cfg_font)

        # 创建文字
        for text, scale, use_typst_text in zip(
            reversed(text_lst),
            reversed(resize_preserving_order(scale_lst, len(text_lst))),
            reversed(resize_preserving_order(use_typst_lst, len(text_lst))),
        ):
            if use_typst_text:
                subtitle = TypstText(text, **kwargs)
            else:
                subtitle = Text(text, font=font, **kwargs)
            is_null = all(item.is_null() for item in subtitle.walk_self_and_descendants())
            if is_null:
                continue

            subtitle.points.scale(scale * base_scale)
            self.place_subtitle(subtitle, range)
            self.subtitle_infos.append(SubtitleInfo(text, range, kwargs, subtitle))

            if surrounding_alpha == 0:
                subtitle_display = subtitle
            else:
                subtitle_display = Group(
                    SurroundingRect(
                        subtitle,
                        color=surrounding_color,
                        stroke_alpha=0,
                        fill_alpha=surrounding_alpha,
                    ),
                    subtitle,
                )
            subtitle_display.fix_in_frame().depth.set(depth)

            if not self.hide_subtitles:
                self.schedule(range.at, subtitle_display.show)
                self.schedule(range.end, subtitle_display.hide)

        return range.copy()

    def place_subtitle(self, subtitle: Text | TypstText, range: TimeRange) -> None:
        """
        被 :meth:`subtitle` 调用以将字幕放置到合适的位置：

        - 对于同一批添加的字幕 ``[a, b]``，则 ``a`` 放在 ``b`` 的上面
        - 如果在上文所述的 ``[a, b]`` 仍存在时，又加入了一个 ``c``，则 ``c`` 放在最上面
        """
        for other in reversed(self.subtitle_infos):
            # 根据 TimelineView 中排列显示标签的经验
            # 这里加了一个 np.isclose 的判断
            # 如果不加可能导致前一个字幕消失但是后一个字幕凭空出现在更上面
            # （但是我没有测试过是否会出现这个bug，只是根据写 TimelineView 时的经验加了 np.isclose）
            if other.range.at <= range.at < other.range.end and not np.isclose(range.at, other.range.end):  # fmt: skip
                subtitle.points.next_to(other.subtitle, UP, buff=2 * SMALL_BUFF)
                return

        buff_to_edge = Config.get.subtitle_to_edge_buff

        if isinstance(subtitle, Text):
            # 相对于 mark_orig 对齐到屏幕底端，这样不同字幕的位置不会上下浮动
            target_y = -Config.get.frame_y_radius + buff_to_edge
            mark_y = subtitle[-1].get_mark_orig()[1]
            subtitle.points.set_x(0).shift(UP * (target_y - mark_y))
        else:
            subtitle.points.to_border(DOWN, buff=buff_to_edge)

    def has_subtitle(self) -> bool:
        return len(self.subtitle_infos) != 0
