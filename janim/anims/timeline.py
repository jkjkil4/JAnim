from __future__ import annotations

import inspect
import itertools as it
import math
import os
import time
import traceback
import types
from abc import ABCMeta, abstractmethod
from bisect import bisect, insort
from collections import defaultdict
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable, Iterable, Self, overload

import moderngl as mgl
import numpy as np
import OpenGL.GL as gl
from PIL import Image

from janim.anims.anim_stack import AnimStack
from janim.anims.animation import (Animation, TimeAligner, TimeRange,
                                   TimeSegments)
from janim.anims.composition import AnimGroup
from janim.anims.updater import updater_params_ctx
from janim.camera.camera import Camera
from janim.camera.camera_info import CameraInfo
from janim.constants import (BLACK, DEFAULT_DURATION,
                             DEFAULT_ITEM_TO_EDGE_BUFF, DOWN, FOREVER,
                             SMALL_BUFF, UP)
from janim.exception import TimelineLookupError
from janim.items.audio import Audio
from janim.items.item import Item
from janim.items.points import Group
from janim.items.shape_matchers import SurroundingRect
from janim.items.svg.typst import TypstText
from janim.items.text import Text
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.base import RenderData, Renderer, create_context
from janim.render.framebuffer import (FRAME_BUFFER_BINDING, blend_context,
                                      create_framebuffer, framebuffer_context,
                                      uniforms)
from janim.render.uniform import get_uniforms_context_var
from janim.typing import JAnimColor, SupportsAnim
from janim.utils.config import Config, ConfigGetter, config_ctx_var
from janim.utils.data import ContextSetter
from janim.utils.iterables import resize_preserving_order
from janim.utils.simple_functions import clip

_ = get_local_strings('timeline')

type RenderCallsFn = Callable[[], list[tuple[Item, Callable[[Item], None]]]]


class Timeline(metaclass=ABCMeta):
    '''
    继承该类并实现 :meth:`construct` 方法，以实现动画的构建逻辑

    调用 :meth:`build` 可以得到构建完成的 :class:`Timeline` 对象
    '''

    CONFIG: Config | None = None
    '''
    在子类中定义该变量可以起到设置配置的作用，例如：

    .. code-block::

        class Example(Timeline):
            CONFIG = Config(
                font=['Consolas', 'LXGW WenKai Lite']
            )

            def construct(self) -> None:
                ...

    另见：:class:`~.Config`
    '''

    # region context

    ctx_var: ContextVar[Timeline | None] = ContextVar('Timeline.ctx_var')

    @staticmethod
    def get_context(raise_exc=True) -> Timeline | None:
        '''
        调用该方法可以得到当前正在构建的 :class:`Timeline` 对象

        - 如果在 :meth:`construct` 方法外调用，且 ``raise_exc=True`` （默认），则抛出 :class:`~.TimelineLookupError`
        '''
        obj = Timeline.ctx_var.get(None)
        if obj is None and raise_exc:
            f_back = inspect.currentframe().f_back
            raise TimelineLookupError(
                _('{name} cannot be used outside of Timeline.construct')
                .format(name=f_back.f_code.co_qualname)
            )
        return obj

    # endregion

    @dataclass
    class ScheduledTask:
        '''
        另见 :meth:`~.Timeline.schedule`
        '''
        at: float
        func: Callable
        args: list
        kwargs: dict

    @dataclass
    class TimeOfCode:
        '''
        标记 :meth:`~.Timeline.construct` 执行到的代码行数所对应的时间
        '''
        time: float
        line: int

    @dataclass
    class PausePoint:
        at: float
        at_previous_frame: bool

    @dataclass
    class PlayAudioInfo:
        '''
        调用 :meth:`~.Timeline.play_audio` 的参数信息
        '''
        audio: Audio
        range: TimeRange
        clip_range: TimeRange

    @dataclass
    class SubtitleInfo:
        '''
        调用 :meth:`~.Timeline.subtitle` 的参数信息
        '''
        text: str
        range: TimeRange
        kwargs: dict
        subtitle: Text | TypstText

    @dataclass
    class AdditionalRenderCallsCallback:
        t_range: TimeRange
        func: RenderCallsFn

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_time: float = 0
        self.times_of_code: list[Timeline.TimeOfCode] = []

        self._frozen_config: list[Config] | None = None

        self.scheduled_tasks: list[Timeline.ScheduledTask] = []
        self.audio_infos: list[Timeline.PlayAudioInfo] = []
        self.subtitle_infos: list[Timeline.SubtitleInfo] = []   # helpful for extracting subtitles

        self.pause_points: list[Timeline.PausePoint] = []

        self.anim_groups: list[AnimGroup] = []
        self.additional_render_calls_callbacks: list[Timeline.AdditionalRenderCallsCallback] = []

        self.time_aligner: TimeAligner = TimeAligner()
        self.item_appearances = Timeline.ItemAppearancesDict(self.time_aligner)

        self.debug_list: list[Item] = []

        self.subtimeline_items: list[TimelineItem] = []

    @abstractmethod
    def construct(self) -> None:
        '''
        继承该方法以实现动画的构建逻辑
        '''
        pass    # pragma: no cover

    build_indent_ctx: ContextVar[int] = ContextVar('Timeline.build_indent_ctx')

    def build(self, *, quiet=False, hide_subtitles=False, show_debug_notice=False) -> BuiltTimeline:
        '''
        构建动画并返回
        '''
        indent = self.build_indent_ctx.get(-2) + 2
        indent_str = ' ' * indent
        with self.with_config(), ContextSetter(self.ctx_var, self), ContextSetter(self.build_indent_ctx, indent):

            self.config_getter = ConfigGetter(config_ctx_var.get())
            self.camera = Camera()
            self.track(self.camera)
            self.hide_subtitles = hide_subtitles
            self.show_debug_notice = show_debug_notice

            if not quiet:   # pragma: no cover
                log.info(indent_str + _('Building "{name}"').format(name=self.__class__.__name__))
                start_time = time.time()

            self._build_frame = inspect.currentframe()

            try:
                self.construct()
            finally:
                self._build_frame = None

            if self.current_time == 0:
                self.forward(DEFAULT_DURATION, _record_lineno=False)    # 使得没有任何前进时，产生一点时间，避免除零以及其它问题
                if not quiet:   # pragma: no cover
                    log.info(
                        indent_str + (
                            _('"{name}" did not produce a duration after construction, '
                              'automatically generated a duration of {duration}s')
                            .format(name=self.__class__.__name__, duration=DEFAULT_DURATION)
                        )
                    )

            for item, appr in self.item_appearances.items():
                appr.stack.detect_change_if_not(item)
                appr.stack.clear_cache()

            built = BuiltTimeline(self)

            if not quiet:   # pragma: no cover
                elapsed = time.time() - start_time
                log.info(
                    indent_str + (
                        _('Finished building "{name}" in {elapsed:.2f} s')
                        .format(name=self.__class__.__name__, elapsed=elapsed)
                    )
                )

        return built

    @contextmanager
    def with_config(self):
        '''
        如果是第一次调用，会在当前 context 的基础上作用定义在 :class:`Timeline` 子类中的 config，并记录

        如果是之后的调用，则会直接设置为已记录的，确保在不同情境下的一致性
        '''
        if self._frozen_config is None:
            cls_config: list[Config] = []
            for sup in self.__class__.mro():
                config: Config | None = getattr(sup, 'CONFIG', None)
                if config is None or config in cls_config:
                    continue
                cls_config.append(config)

            self._frozen_config = [*config_ctx_var.get(), *reversed(cls_config)]

        token = config_ctx_var.set(self._frozen_config)
        try:
            yield
        finally:
            config_ctx_var.reset(token)

    # region schedule

    def schedule(self, at: float, func: Callable, *args, **kwargs) -> None:
        '''
        计划执行

        会在进度达到 ``at`` 时，对 ``func`` 进行调用，
        可传入 ``*args`` 和 ``**kwargs``
        '''
        task = Timeline.ScheduledTask(self.time_aligner.align_t(at), func, args, kwargs)
        insort(self.scheduled_tasks, task, key=lambda x: x.at)

    def schedule_and_detect_changes(self, at: float, func: Callable, *args, **kwargs) -> None:
        '''
        与 :meth:`schedule` 类似，但是在调用 ``func`` 后会记录变化的物件的状态
        '''
        def wrapper(*args, **kwargs) -> None:
            func(*args, **kwargs)
            self.detect_changes_of_all()
        self.schedule(at, wrapper, *args, *kwargs)

    def timeout(self, delay: float, func: Callable, *args, **kwargs) -> None:
        '''
        相当于 `schedule(self.current_time + delay, func, *args, **kwargs)`
        '''
        self.schedule(self.current_time + delay, func, *args, **kwargs)

    def timeout_and_detect_changes(self, delay: float, func: Callable, *args, **kwargs) -> None:
        '''
        与 :meth:`timeout` 类似，但是在调用 ``func`` 后会记录变化的物件的状态
        '''
        def wrapper(*args, **kwargs) -> None:
            func(*args, **kwargs)
            self.detect_changes_of_all()
        self.timeout(delay, wrapper, *args, *kwargs)

    # endregion

    # region progress

    def forward(self, dt: float = DEFAULT_DURATION, *, _detect_changes=True, _record_lineno=True):
        '''
        向前推进 ``dt`` 秒
        '''
        if dt < 0:
            raise ValueError(_('dt can\'t be negative'))

        if _detect_changes:
            self.detect_changes_of_all()

        to_time = self.current_time + dt

        while self.scheduled_tasks and self.scheduled_tasks[0].at <= to_time:
            task = self.scheduled_tasks.pop(0)
            self.current_time = task.at
            task.func(*task.args, **task.kwargs)

        self.current_time = to_time

        if _record_lineno:
            self.times_of_code.append(
                Timeline.TimeOfCode(
                    self.current_time,
                    self.get_construct_lineno() or -1
                )
            )

    def forward_to(self, t: float, *, _detect_changes=True) -> None:
        '''
        向前推进到 ``t`` 秒的时候
        '''
        self.forward(t - self.current_time, _detect_changes=_detect_changes)

    def prepare(self, *anims: SupportsAnim, at: float = 0, name: str | None = 'prepare', **kwargs) -> TimeRange:
        self.detect_changes_of_all()
        group = AnimGroup(*anims, at=at + self.current_time, name=name, **kwargs)
        group.finalize()
        # 这里的 anim_groups.append 和 AnimStack.append 是不同的，后者已在 finalize 中被调用
        self.anim_groups.append(group)
        return group.t_range

    def play(self, *anims: SupportsAnim, name: str | None = 'play', **kwargs) -> TimeRange:
        t_range = self.prepare(*anims, name=name, **kwargs)
        self.forward_to(t_range.end, _detect_changes=False)
        return t_range

    def pause_point(
        self,
        *,
        offset: float = 0,
        at_previous_frame: bool = True
    ) -> None:
        '''
        标记在预览界面中，执行到当前时间点时会暂停

        - ``at_previous_frame`` 控制是在前一帧暂停（默认）还是在当前帧暂停
        - ``offset`` 表示偏移多少秒，例如 ``offset=2`` 则是当前位置 2s 后
        - 在 GUI 界面中，可以使用 ``Ctrl+左方向键`` 快速移动到前一个暂停点，``Ctrl+右方向键`` 快速移动到后一个
        '''
        self.pause_points.append(Timeline.PausePoint(self.current_time + offset, at_previous_frame))

    # endregion

    def aas(
        self,
        file_path: str,
        subtitle: str | Iterable[str],
        **kwargs
    ) -> TimeRange:
        '''
        :meth:`audio_and_subtitle` 的简写
        '''
        return self.audio_and_subtitle(file_path, subtitle, **kwargs)

    def audio_and_subtitle(
        self,
        file_path: str,
        subtitle: str | Iterable[str],
        *,
        clip: tuple[float, float] | None | types.EllipsisType = ...,
        delay: float = 0,
        mul: float | Iterable[float] | None = None,
        **subtitle_kwargs
    ) -> TimeRange:
        '''
        播放音频，并在对应的区间显示字幕

        - 如果 ``clip=...`` （默认，省略号），则表示自动确定裁剪区间，将前后的空白去除（可以传入 ``clip=None`` 禁用自动裁剪）
        - 如果 ``mul`` 不是 ``None``，则会将音频振幅乘以该值
        '''
        audio = Audio(file_path)
        if mul is not None:
            audio.mul(mul)

        if clip is ...:
            recommended = audio.recommended_range()
            if recommended is None:
                clip = None
            else:
                clip = (math.floor(recommended[0] * 10) / 10,
                        math.ceil(recommended[1] * 10) / 10)

        t = self.play_audio(audio, delay=delay, clip=clip)
        self.subtitle(subtitle, t, **subtitle_kwargs)

        return t

    # region audio

    def play_audio(
        self,
        audio: Audio,
        *,
        delay: float = 0,
        begin: float = 0,
        end: float = -1,
        clip: tuple[float, float] | None = None,
    ) -> TimeRange:
        '''
        在当前位置播放音频

        - 可以指定 ``begin`` 和 ``end`` 表示裁剪区段
        - 可以指定在当前位置往后 ``delay`` 秒才开始播放
        - 若指定 ``clip``，则会覆盖 ``begin`` 和 ``end`` （可以将 ``clip`` 视为这二者的简写）

        返回值表示播放的时间段
        '''
        if clip is not None:
            begin, end = clip

        if end == -1:
            end = audio.duration()
        duration = end - begin
        at = self.current_time + delay

        info = Timeline.PlayAudioInfo(audio,
                                      TimeRange(at, at + duration),
                                      TimeRange(begin, end))
        self.audio_infos.append(info)

        return info.range.copy()

    def has_audio(self) -> bool:
        '''
        该 Timeline 自身是否有可以播放的音频
        '''
        return len(self.audio_infos) != 0

    def has_audio_for_all(self) -> bool:
        '''
        考虑所有子 Timeline，是否有可以播放的音频
        '''
        if len(self.audio_infos) != 0:
            return True
        return any(
            item._built.timeline.has_audio_for_all()
            for item in self.subtimeline_items
        )

    # endregion

    # region subtitle

    @overload
    def subtitle(
        self,
        text: str | Iterable[str],
        duration: float = 1,
        delay: float = 0,
        scale: float | Iterable[float] = 0.8,
        use_typst_text: bool | Iterable[bool] = False,
        surrounding_color: JAnimColor = BLACK,
        surrounding_alpha: float = 0.5,
        font: str | Iterable[str] = [],
        depth: float = -1e5,
        **kwargs
    ) -> TimeRange: ...

    @overload
    def subtitle(self, text: str | Iterable[str], range: TimeRange, **kwargs) -> TimeRange: ...

    def subtitle(
        self,
        text: str | Iterable[str],
        duration: float = 1,
        delay: float = 0,
        scale: float | Iterable[float] = 1,
        base_scale: float = 0.8,
        use_typst_text: bool | Iterable[bool] = False,
        surrounding_color: JAnimColor = BLACK,
        surrounding_alpha: float = 0.5,
        font: str | Iterable[str] = [],
        depth: float = -1e5,
        **kwargs
    ) -> TimeRange:
        '''
        添加字幕

        - 文字可以传入一个列表，纵向排列显示
        - 可以指定在当前位置往后 ``delay`` 秒才显示
        - ``duration`` 表示持续时间
        - ``scale`` 表示对文字的缩放，默认为 ``0.8``，可以传入列表表示对各个文字的缩放
        - ``use_typst_text`` 表示是否使用 :class:`TypstText`，可以传入列表表示各个文字是否使用

        返回值表示显示的时间段
        '''
        # 处理参数
        text_lst = [text] if isinstance(text, str) else text
        scale_lst = [scale] if not isinstance(scale, Iterable) else scale
        use_typst_lst = [use_typst_text] if not isinstance(use_typst_text, Iterable) else use_typst_text

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
        for text, scale, use_typst_text in zip(reversed(text_lst),
                                               reversed(resize_preserving_order(scale_lst, len(text_lst))),
                                               reversed(resize_preserving_order(use_typst_lst, len(text_lst)))):
            if use_typst_text:
                subtitle = TypstText(text, **kwargs)
            else:
                subtitle = Text(text, font=font, **kwargs)
            subtitle.points.scale(scale * base_scale)
            self.place_subtitle(subtitle, range)
            self.subtitle_infos.append(Timeline.SubtitleInfo(text, range, kwargs, subtitle))

            subtitle_group = Group(
                SurroundingRect(subtitle,
                                color=surrounding_color,
                                stroke_alpha=0,
                                fill_alpha=surrounding_alpha),
                subtitle
            ).fix_in_frame()
            subtitle_group.depth.set(depth)

            if not self.hide_subtitles:
                self.schedule(range.at, subtitle_group.show)
                self.schedule(range.end, subtitle_group.hide)

        return range.copy()

    def place_subtitle(self, subtitle: Text | TypstText, range: TimeRange) -> None:
        '''
        被 :meth:`subtitle` 调用以将字幕放置到合适的位置：

        - 对于同一批添加的字幕 ``[a, b]``，则 ``a`` 放在 ``b`` 的上面
        - 如果在上文所述的 ``[a, b]`` 仍存在时，又加入了一个 ``c``，则 ``c`` 放在最上面
        '''
        for other in reversed(self.subtitle_infos):
            # 根据 TimelineView 中排列显示标签的经验
            # 这里加了一个 np.isclose 的判断
            # 如果不加可能导致前一个字幕消失但是后一个字幕凭空出现在更上面
            # （但是我没有测试过是否会出现这个bug，只是根据写 TimelineView 时的经验加了 np.isclose）
            if other.range.at <= range.at < other.range.end and not np.isclose(range.at, other.range.end):
                subtitle.points.next_to(other.subtitle, UP, buff=2 * SMALL_BUFF)
                return

        if isinstance(subtitle, Text):
            # 相对于 mark_orig 对齐到屏幕底端，这样不同字幕的位置不会上下浮动
            target_y = -Config.get.frame_y_radius + DEFAULT_ITEM_TO_EDGE_BUFF
            subtitle.points.set_x(0).shift(UP * (target_y - subtitle[-1].get_mark_orig()[1]))
        else:
            subtitle.points.to_border(DOWN)

    def has_subtitle(self) -> bool:
        return len(self.subtitle_infos) != 0

    # endregion

    # region ItemAppearance

    class ItemAppearance:
        '''
        包含与物件显示有关的对象

        - ``self.stack`` 即 :class:`~.AnimStack` 对象

        - ``self.visiblility`` 是一个列表，存储物件显示/隐藏的时间点
          - 列表中偶数下标（0、2、...）的表示开始显示的时间点，奇数下标（1、3、...）的表示隐藏的时间点
          - 例如，如果列表中是 ``[3, 4, 8]``，则表示在第 3s 显示，第 4s 隐藏，并且在第 8s 后一直显示
          - 这种记录方式是 :meth:`Timeline.is_visible`、:meth:`Timeline.show`、:meth:`Timeline.hide` 运作的基础

        - ``self.renderer`` 表示所使用的渲染器对象
        '''
        def __init__(self, item: Item, aligner: TimeAligner):
            self.stack = AnimStack(item, aligner)
            self.visibility: list[float] = []
            self.renderer: Renderer | None = None
            self.render_disabled: bool = False

        def is_visible_at(self, t: float) -> bool:
            '''
            在 ``t`` 时刻，物件是否可见
            '''
            idx = bisect(self.visibility, t)
            return idx % 2 == 1

        def render(self, data: Item) -> None:
            if self.renderer is None:
                self.renderer = data.create_renderer()
            self.renderer.render(data)

    class ItemAppearancesDict(defaultdict[Item, ItemAppearance]):
        def __init__(self, time_aligner: TimeAligner):
            super().__init__(lambda key: Timeline.ItemAppearance(key, time_aligner))

        def __missing__(self, key: Item) -> Timeline.ItemAppearance:
            self[key] = value = self.default_factory(key)
            return value

    # region ItemAppearance.stack

    def track(self, item: Item) -> None:
        '''
        使得 ``item`` 在每次 ``forward`` 和 ``play`` 时都会被自动调用 :meth:`~.Item.detect_change`
        '''
        self.item_appearances[item]

    def track_item_and_descendants(self, item: Item, *, root_only: bool = False) -> None:
        '''
        相当于对 ``item`` 及其所有的后代物件调用 :meth:`track`
        '''
        for subitem in item.walk_self_and_descendants(root_only):
            self.item_appearances[subitem]

    def detect_changes_of_all(self) -> None:
        '''
        检查物件的变化并将变化记录为 :class:`~.Display`
        '''
        for item, appr in self.item_appearances.items():
            appr.stack.detect_change(item, self.current_time)

    def detect_changes(self, items: Iterable[Item]) -> None:
        '''
        检查指定的列表中物件的变化，并将变化记录为 :class:`~.Display`

        （仅检查自身而不包括子物件的）
        '''
        for item in items:
            self.item_appearances[item].stack.detect_change(item, self.current_time)

    def compute_item[T](self, item: T, as_time: float, readonly: bool) -> T:
        '''
        另见 :meth:`~.AnimStack.compute`
        '''
        return self.item_appearances[item].stack.compute(as_time, readonly)

    def item_current[T: Item](self, item: T, *, as_time: float | None = None, root_only: bool = False) -> T:
        '''
        另见 :meth:`~.Item.current`
        '''
        if as_time is None:
            params = updater_params_ctx.get(None)
            if params is not None:
                as_time = params.global_t
        if as_time is None:
            as_time = Animation.global_t_ctx.get(None)

        if as_time is None:
            return item.copy(root_only=root_only)

        root = self.compute_item(item, as_time, False)
        if not root_only:
            assert not root.children and root.stored_children is not None
            root.stored = False
            root.add(*[self.item_current(sub, as_time=as_time) for sub in root.stored_children])
            root.reset_refresh()
        return root

    # endregion

    # region ItemAppearance.visibility

    def is_visible(self, item: Item) -> bool:
        '''
        判断特定的物件目前是否可见

        另见：:meth:`show`、:meth:`hide`
        '''
        # 在运行 construct 过程中，params 是 None，返回值表示最后状态是否可见
        params = updater_params_ctx.get(None)
        if params is None:
            return len(self.item_appearances[item].visibility) % 2 == 1

        # 在 updater 的回调函数中，params 不是 None，返回值表示在这时是否可见
        return self.item_appearances[item].is_visible_at(params.global_t)

    def is_displaying(self, item: Item) -> bool:
        from janim.utils.deprecation import deprecated
        deprecated(
            'Timeline.is_displaying',
            'Timeline.is_visible',
            remove=(3, 3)
        )
        return self.is_visible(item)

    def _show(self, item: Item) -> None:
        gaps = self.item_appearances[item].visibility
        if len(gaps) % 2 != 1:
            gaps.append(self.time_aligner.align_t(self.current_time))

    def show(self, *roots: Item, root_only=False) -> None:
        '''
        显示物件
        '''
        for root in roots:
            for item in root.walk_self_and_descendants(root_only):
                self._show(item)

    def _hide(self, item: Item) -> None:
        gaps = self.item_appearances[item].visibility
        if len(gaps) % 2 == 1:
            gaps.append(self.time_aligner.align_t(self.current_time))

    def hide(self, *roots: Item, root_only=False) -> None:
        '''
        隐藏物件
        '''
        for root in roots:
            for item in root.walk_self_and_descendants(root_only):
                self._hide(item)

    def hide_all(self) -> None:
        '''
        隐藏显示中的所有物件
        '''
        t = self.time_aligner.align_t(self.current_time)
        for appr in self.item_appearances.values():
            gaps = appr.visibility
            if len(gaps) % 2 == 1:
                gaps.append(t)

    def cleanup_display(self) -> None:
        from janim.utils.deprecation import deprecated
        deprecated(
            'Timeline.cleanup_display',
            'Timeline.hide_all',
            remove=(3, 3)
        )
        self.hide_all()

    def visible_items(self) -> list[Item]:
        return [
            item
            for item, appr in self.item_appearances.items()
            if len(appr.visibility) % 2 == 1
        ]

    def add_additional_render_calls_callback(
        self,
        t_range: TimeRange,
        func: RenderCallsFn
    ) -> None:
        self.additional_render_calls_callbacks.append(Timeline.AdditionalRenderCallsCallback(t_range, func))

    # endregion

    # region lineno

    def get_construct_lineno(self) -> int | None:
        '''
        得到当前在 :meth:`construct` 中执行到的行数
        '''
        frame = inspect.currentframe().f_back
        while frame is not None:
            f_back = frame.f_back

            if f_back is self._build_frame and frame.f_code.co_filename == inspect.getfile(self.__class__):
                return frame.f_lineno

            frame = f_back

        return None     # pragma: no cover

    def get_lineno_at_time(self, time: float):
        '''
        根据 ``time`` 得到对应执行到的行数
        '''
        toc = self.times_of_code
        if not toc:
            return -1

        idx = bisect(toc, time, key=lambda x: x.time)
        idx = clip(idx, 0, len(toc) - 1)
        return toc[idx].line

    # endregion

    # region debug

    def debug(self, item: Item, msg: str | None = None) -> None:
        '''
        将物件的动画栈显示在时间轴中

        .. tip::

            显示在时间轴中的一个黄色扁条表示在哪些区段中物件是可见的

        .. warning::

            有些动画是覆盖性的，例如直接数据改变（``Display``） 和 ``.anim`` （``MethodTransform``），不要因为没有看到预期的栈结构而感到困惑
        '''
        if self.show_debug_notice:
            f_back = inspect.currentframe().f_back
            filename = os.path.basename(f_back.f_code.co_filename)
            obj_and_loc = _('Called self.debug({repr}) at {loc}') \
                .format(repr=repr(item), loc=f'{filename}:{f_back.f_lineno}')
            if msg is None:
                log.info(obj_and_loc)
            else:
                log.info(obj_and_loc + '\nmsg=' + msg)
        self.debug_list.append(item)

    @staticmethod
    def fmt_time(t: float) -> str:
        time = round(t, 3)

        minutes = int(time // 60)
        time %= 60

        hours = minutes // 60
        minutes %= 60

        seconds = math.floor(time)
        ms = round((time - seconds) * 1e3)

        times = []
        if hours != 0:
            times.append(f'{hours}h')
        times.append(f'{minutes:>3d}m' if minutes != 0 else ' ' * 4)
        times.append(f'{seconds:>3d}s')
        times.append(f'{ms:>4d}ms' if ms != 0 else ' ' * 6)

        return "".join(times)

    def dbg_time(self, ext_msg: str = '') -> None:  # pragma: no cover
        if ext_msg:
            ext_msg = f'[{ext_msg}]  '

        time = self.fmt_time(self.current_time)

        log.info(f't={time}  {ext_msg}at construct.{self.get_construct_lineno()}')

    # endregion


class SourceTimeline(Timeline):
    '''
    与 :class:`Timeline` 相比，会在背景显示源代码
    '''
    def source_object(self) -> object:
        return self.__class__

    def build(self, *, quiet=False, hide_subtitles=False, show_debug_notice=False) -> BuiltTimeline:
        from janim.items.text import SourceDisplayer
        with ContextSetter(self.ctx_var, self), self.with_config():
            self.source_displayer = SourceDisplayer(self.source_object(), depth=10000).show()
        return super().build(quiet=quiet, hide_subtitles=hide_subtitles, show_debug_notice=show_debug_notice)


class BuiltTimeline:
    '''
    运行 :meth:`Timeline.build` 后返回的实例
    '''
    def __init__(self, timeline: Timeline):
        self.timeline = timeline
        self.duration = timeline.time_aligner.align_t(timeline.current_time)

        self.visible_item_segments = TimeSegments(
            (
                (item, appr)
                for item, appr in timeline.item_appearances.items()
            ),
            lambda x: (
                TimeRange(*range) if len(range) == 2 else TimeRange(*range, self.duration + 1)
                for range in it.batched(x[1].visibility, 2)
            )
        )
        self.visible_additional_callbacks_segments = TimeSegments(
            self.timeline.additional_render_calls_callbacks,
            lambda x: (
                x.t_range if x.t_range.end is not FOREVER else TimeRange(x.t_range.at, self.duration + 1)
            )
        )

        self._time: float = 0

        self.capture_ctx: mgl.Context | None = None

    @property
    def cfg(self) -> Config | ConfigGetter:
        return self.timeline.config_getter

    def get_audio_samples_of_frame(
        self,
        fps: float,
        framerate: int,
        frame: int,
        *,
        count: int = 1
    ) -> np.ndarray:
        '''
        提取特定帧的音频流
        '''
        begin = frame / fps
        end = (frame + count) / fps
        channels = self.cfg.audio_channels

        output_sample_count = math.floor(end * framerate) - math.floor(begin * framerate)
        result = np.zeros((output_sample_count, channels), dtype=np.int16)

        # 合并自身的 audio
        for info in self.timeline.audio_infos:
            if end < info.range.at or begin > info.range.end:
                continue

            audio = info.audio

            frame_begin = int((begin - info.range.at + info.clip_range.at) * audio.framerate)
            frame_end = int((end - info.range.at + info.clip_range.at) * audio.framerate)

            clip_begin = max(0, int(audio.framerate * info.clip_range.at))
            clip_end = min(audio.sample_count(), int(audio.framerate * info.clip_range.end))

            left_blank = max(0, clip_begin - frame_begin)
            right_blank = max(0, frame_end - clip_end)

            data = audio._samples.data[max(clip_begin, frame_begin): min(clip_end, frame_end)]

            if left_blank != 0 or right_blank != 0:
                # channels = data.shape[1]
                data = np.concatenate([
                    np.zeros((left_blank, channels), dtype=np.int16),
                    data,
                    np.zeros((right_blank, channels), dtype=np.int16)
                ])

            result += resize_preserving_order(data, output_sample_count)

        # 合并子 Timeline 的 audio
        for item in self.timeline.subtimeline_items:
            built = item._built
            frame_offset = int(item.at * fps)

            data = built.get_audio_samples_of_frame(fps, framerate, frame - frame_offset, count=count)
            result += resize_preserving_order(data, output_sample_count)

        return result

    def current_camera_info(self) -> CameraInfo:
        return self.timeline.compute_item(self.timeline.camera, self._time, True).points.info

    def render_all(self, ctx: mgl.Context, global_t: float, *, blend_on: bool = True) -> bool:
        '''
        渲染所有可见物件
        '''
        timeline = self.timeline
        global_t = timeline.time_aligner.align_t_for_render(global_t)
        # 使得最后一帧采用略提早一点点的时间渲染，使得一些结束在结尾的动画不突变
        if global_t == self.duration:
            global_t -= 1e-4
        self._time = global_t
        try:
            with ContextSetter(Animation.global_t_ctx, global_t),   \
                 ContextSetter(Timeline.ctx_var, self.timeline),    \
                 self.timeline.with_config():
                camera = timeline.compute_item(timeline.camera, global_t, True)
                camera_info = camera.points.info
                anti_alias_radius = self.cfg.anti_alias_width / 2 * camera_info.scaled_factor

                with blend_context(ctx, True) if blend_on else nullcontext(), \
                     uniforms(ctx,
                              JA_FRAMEBUFFER=FRAME_BUFFER_BINDING,
                              JA_CAMERA_SCALED_FACTOR=camera_info.scaled_factor,
                              JA_VIEW_MATRIX=camera_info.view_matrix.T.flatten(),
                              JA_FIXED_DIST_FROM_PLANE=camera_info.fixed_distance_from_plane,
                              JA_PROJ_MATRIX=camera_info.proj_matrix.T.flatten(),
                              JA_FRAME_RADIUS=camera_info.frame_radius,
                              JA_ANTI_ALIAS_RADIUS=anti_alias_radius), \
                     ContextSetter(Renderer.data_ctx, RenderData(ctx=ctx,
                                                                 camera_info=camera_info,
                                                                 anti_alias_radius=anti_alias_radius)):
                    render_datas: list[tuple[Timeline.ItemAppearance, Item]] = []
                    # 反向遍历一遍所有物件，这是为了让一些效果标记原有的物件不进行渲染
                    # （会把所应用的物件的 render_disabled 置为 True，所以在下面可以判断这个变量过滤掉它们）
                    for _, appr in reversed(self.visible_item_segments.get(global_t)):
                        if not appr.is_visible_at(global_t):
                            continue
                        data = appr.stack.compute(global_t, True)
                        data._mark_render_disabled()
                        render_datas.append((appr, data))
                    # 添加额外的渲染调用，例如 Transform 产生的
                    # 这里也有可能产生 render_disabled 标记
                    additional: list[list[tuple[Item, Callable[[Item], None]]]] = []
                    for rcc in self.visible_additional_callbacks_segments.get(global_t):
                        if rcc.t_range.end is FOREVER:
                            if not rcc.t_range.at <= global_t:
                                continue
                        else:
                            if not rcc.t_range.at <= global_t < rcc.t_range.end:
                                continue
                        additional.append(rcc.func())
                    # 剔除被标记 render_disabled 的物件，得到 render_items_final
                    render_datas_final: list[tuple[Item, Callable]] = []
                    for appr, data in render_datas:
                        if appr.render_disabled:
                            appr.render_disabled = False    # 重置，因为每次都要重新标记
                            continue
                        render_datas_final.append((data, appr.render))
                    render_datas_final.extend(it.chain(*additional))
                    # 按深度排序
                    render_datas_final.sort(key=lambda x: x[0].depth, reverse=True)
                    # 渲染
                    blending = get_uniforms_context_var(ctx).get().get('JA_BLENDING')
                    for data, render in render_datas_final:
                        render(data)
                        # 如果没有 blending，我们认为当前是在向透明 framebuffer 绘制
                        # 所以每次都需要使用 glFlush 更新 framebuffer 信息使得正确渲染
                        if not blending:
                            gl.glFlush()

        except Exception:
            traceback.print_exc()
            return False

        return True

    def capture(self, global_t: float, *, transparent: bool = True) -> Image.Image:
        if self.capture_ctx is None:
            try:
                self.capture_ctx = create_context(standalone=True, require=430)
            except ValueError:
                self.capture_ctx = create_context(standalone=True, require=330)

            pw, ph = self.cfg.pixel_width, self.cfg.pixel_height
            self.capture_fbo = create_framebuffer(self.capture_ctx, pw, ph)

        fbo = self.capture_fbo
        with framebuffer_context(self.capture_fbo):
            fbo.clear(*self.cfg.background_color.rgb, not transparent)
            if transparent:
                gl.glFlush()
            self.render_all(self.capture_ctx, global_t, blend_on=not transparent)

        return Image.frombytes(
            "RGBA", fbo.size, fbo.read(components=4),
            "raw", "RGBA", 0, -1
        )

    def to_item(self, **kwargs) -> TimelineItem:
        '''
        使用该方法可以在一个 Timeline 中插入另一个 Timeline

        例如：

        .. code-block:: python

            class Sub1(Timeline):
                def construct(self):
                    text = Text('text from Sub1')
                    text.points.shift(UP)
                    self.play(
                        Rotate(text, TAU, about_point=LEFT * 2),
                        duration=4
                    )


            class Sub2(Timeline):
                def construct(self):
                    text = Text('text from Sub2')
                    text.points.shift(DOWN)
                    self.play(
                        Rotate(text, TAU, about_point=RIGHT * 2),
                        duration=4
                    )


            class Test(Timeline):
                def construct(self):
                    tl1 = Sub1().build().to_item().show()
                    tl2 = Sub2().build().to_item().show()
                    self.forward_to(tl2.end)

        这个例子中，在 ``Test`` 中插入了 ``Sub1`` 和 ``Sub2``

        额外参数：

        - ``delay``: 延迟多少秒开始该 Timeline 的播放
        - ``first_frame_duration``: 第一帧持续多少秒
        - ``keep_last_frame``: 是否在 Timeline 结束后仍然保留最后一帧的显示
        '''
        return TimelineItem(self, **kwargs)

    def to_playback_control_item(self, **kwargs) -> TimelinePlaybackControlItem:
        '''
        使用该方法可以在一个 Timeline 中插入另一个 Timeline

        并且与 :class:`~.Video` 类似，可以使用 ``start``、``stop`` 以及 ``seek`` 控制播放进度

        例：

        .. code-block:: python

            class Sub(Timeline):
                def construct(self):
                    self.play(
                        ItemUpdater(
                            None,
                            lambda p: Text(f'{p.global_t:.2f}')
                        ),
                        duration=8
                    )


            class Test(Timeline):
                def construct(self):
                    sub = Sub().build().to_playback_control_item().show()
                    sub.start()
                    self.forward(2)
                    sub.start(speed=0.1)
                    self.forward(2)
                    sub.seek(0).start(speed=4)
                    self.forward(2)

        注意：在默认情况下未开始播放，需要使用 ``start`` 以开始播放

        额外参数：

        - ``keep_last_frame``: 是否在 Timeline 结束后仍然保留最后一帧的显示
        '''
        return TimelinePlaybackControlItem(self, **kwargs)


class TimelineItem(Item):
    '''
    详见 :meth:`BuiltTimeline.to_item`
    '''

    class TIRenderer(Renderer):
        def render(self, item: TimelineItem):
            t = Animation.global_t_ctx.get() - item.at

            if 0 <= t <= item.duration:
                if t < item.first_frame_duration:
                    item._built.render_all(self.data_ctx.get().ctx, 0, blend_on=False)
                else:
                    item._built.render_all(self.data_ctx.get().ctx, t - item.first_frame_duration, blend_on=False)
            elif item.keep_last_frame and t > item.duration:
                item._built.render_all(self.data_ctx.get().ctx, item._built.duration, blend_on=False)

    renderer_cls = TIRenderer

    def __init__(
        self,
        built: BuiltTimeline,
        *,
        delay: float = 0,
        first_frame_duration: float = 0,
        keep_last_frame: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._built = built
        self.at = self.timeline.current_time + delay
        self.first_frame_duration = first_frame_duration
        self.duration = first_frame_duration + self._built.duration
        self.keep_last_frame = keep_last_frame

        parent_timeline = Timeline.get_context(raise_exc=False)
        if parent_timeline is not None:
            parent_timeline.subtimeline_items.append(self)

    def start(self) -> Self:
        '''
        从当前时刻开始播放子时间轴，在此时刻之前保持显示第一帧
        '''
        parent_timeline = Timeline.get_context()
        current_time = parent_timeline.current_time
        if self.at > current_time:
            self.at = current_time
        self.first_frame_duration = current_time - self.at
        self.duration = self.first_frame_duration + self._built.duration
        return self

    @property
    def end(self) -> float:
        return self.at + self.duration


class PlaybackControl:
    def __init__(self, *args, loop: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.loop = loop

        self.timeline = Timeline.get_context()

        self.actions: list[tuple[float, float, float]] = []

    def start(self, *, speed: int = 1) -> Self:
        if not self.actions:
            base = 0
        else:
            x, y, last_speed = self.actions[-1]
            base = y + (self.timeline.current_time - x) * last_speed

        self.actions.append((self.timeline.current_time,
                             base,
                             speed))
        return self

    def stop(self) -> Self:
        self.start(speed=0)
        return self

    def seek(self, t: float) -> Self:
        if not self.actions:
            speed = 0
        else:
            speed = self.actions[-1][2]
        self.actions.append((self.timeline.current_time,
                             t,
                             speed))
        return self

    def compute_time(self, t: float, total: float | None = None) -> float:
        if not self.actions:
            return 0
        idx = bisect(self.actions, t, key=lambda v: v[0]) - 1
        if idx < 0:
            return 0
        x, y, speed = self.actions[idx]
        result = y + (t - x) * speed

        if total is not None and self.loop:
            return result % total
        return result


class TimelinePlaybackControlItem(PlaybackControl, Item):
    '''
    详见 :meth:`BuiltTimeline.to_playback_control_item`
    '''

    class TPCIRenderer(Renderer):
        def render(self, item: TimelinePlaybackControlItem):
            t = Animation.global_t_ctx.get()
            t = item.compute_time(t, item.duration)
            t = max(0, t)
            if 0 <= t <= item.duration:
                item._built.render_all(self.data_ctx.get().ctx, t, blend_on=False)
            elif item.keep_last_frame and t > item.duration:
                item._built.render_all(self.data_ctx.get().ctx, item._built.duration, blend_on=False)

    renderer_cls = TPCIRenderer

    def __init__(self, built: BuiltTimeline, *, keep_last_frame: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._built = built
        self.duration = self._built.duration
        self.keep_last_frame = keep_last_frame
