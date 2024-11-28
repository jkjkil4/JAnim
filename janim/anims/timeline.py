from __future__ import annotations

import heapq
import inspect
import math
import time
import traceback
import types
from abc import ABCMeta, abstractmethod
from bisect import bisect, insort
from collections import defaultdict
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable, Iterable, Self, overload

import moderngl as mgl
import numpy as np
from PIL import Image

from janim.anims.animation import Animation, TimeRange
from janim.anims.composition import AnimGroup
from janim.anims.display import Display
from janim.anims.updater import updater_params_ctx
from janim.camera.camera import Camera
from janim.camera.camera_info import CameraInfo
from janim.constants import (BLACK, DEFAULT_DURATION,
                             DEFAULT_ITEM_TO_EDGE_BUFF, DOWN, SMALL_BUFF, UP)
from janim.exception import TimelineLookupError
from janim.items.audio import Audio
from janim.items.item import DynamicItem, Item
from janim.items.points import Group
from janim.items.shape_matchers import SurroundingRect
from janim.items.svg.typst import TypstText
from janim.items.text.text import Text
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.base import RenderData, Renderer, set_global_uniforms
from janim.typing import JAnimColor
from janim.utils.config import Config, ConfigGetter, config_ctx_var
from janim.utils.data import ContextSetter, History
from janim.utils.iterables import resize_preserving_order
from janim.utils.simple_functions import clip

_ = get_local_strings('timeline')


class Timeline(metaclass=ABCMeta):
    '''
    继承该类并实现 :meth:`construct` 方法，以实现动画的构建逻辑

    调用 :meth:`build` 可以得到构建完成的动画对象
    '''

    # region config

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

    class _WithConfig:
        def __init__(self, cls: type[Timeline]):
            self.cls = cls

            self.lst: list[Config] = []
            for sup in self.cls.mro():
                config: Config | None = getattr(sup, 'CONFIG', None)
                if config is None or config in self.lst:
                    continue
                self.lst.append(config)

            self.lst.reverse()

        def __enter__(self) -> Self:
            lst = [*config_ctx_var.get(), *self.lst]
            self.token = config_ctx_var.set(lst)
            return self

        def __exit__(self, exc_type, exc_value, tb) -> None:
            config_ctx_var.reset(self.token)

    @classmethod
    def with_config(cls) -> _WithConfig:
        '''
        使用定义在 :class:`Timeline` 子类中的 config
        '''
        return cls._WithConfig(cls)

    # endregion

    # region context

    ctx_var: ContextVar[Timeline | None] = ContextVar('Timeline.ctx_var', default=None)

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
    class TimeOfCode:
        '''
        标记 :meth:`~.Timeline.construct` 执行到的代码行数所对应的时间
        '''
        time: float
        line: int

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
        subtitle: Text

    @dataclass
    class PausePoint:
        at: float
        at_previous_frame: bool

    class ItemHistory:
        def __init__(self):
            self.history: History[Item | DynamicItem] = History()
            self.history_without_dynamic: History[Item] = History()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_time: float = 0
        self.times_of_code: list[Timeline.TimeOfCode] = []

        self.scheduled_tasks: list[Timeline.ScheduledTask] = []
        self.anims: list[AnimGroup] = []
        self.display_anims: list[Display] = []
        self.audio_infos: list[Timeline.PlayAudioInfo] = []
        self.subtitle_infos: list[Timeline.SubtitleInfo] = []   # helpful for extracting subtitles

        self.pause_points: list[Timeline.PausePoint] = []

        self.items_history: defaultdict[Item, Timeline.ItemHistory] = defaultdict(Timeline.ItemHistory)
        self.item_display_times: dict[Item, int] = {}

    @abstractmethod
    def construct(self) -> None:
        '''
        继承该方法以实现动画的构建逻辑
        '''
        pass    # pragma: no cover

    def build(self, *, quiet=False, hide_subtitles=False) -> TimelineAnim:
        '''
        构建动画并返回
        '''
        with self.with_config(), ContextSetter(self.ctx_var, self):

            self.config_getter = ConfigGetter(config_ctx_var.get())
            self.camera = Camera()
            self.track(self.camera)
            self.hide_subtitles = hide_subtitles

            if not quiet:   # pragma: no cover
                log.info(_('Building "{name}"').format(name=self.__class__.__name__))
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
                        _('"{name}" did not produce a duration after construction, '
                          'automatically generated a duration of {duration}s')
                        .format(name=self.__class__.__name__, duration=DEFAULT_DURATION)
                    )

            self.cleanup_display()

            for item, ih in self.items_history.items():
                if ih.history.has_record():
                    continue
                item_copy = item.store()
                ih.history.record_as_time(0, item_copy)
                ih.history_without_dynamic.record_as_time(0, item_copy)

            global_anim = TimelineAnim(self)

            if not quiet:   # pragma: no cover
                elapsed = time.time() - start_time
                log.info(
                    _('Finished building "{name}" in {elapsed:.2f} s')
                    .format(name=self.__class__.__name__, elapsed=elapsed)
                )

        return global_anim

    def schedule(self, at: float, func: Callable, *args, **kwargs) -> None:
        '''
        计划执行

        会在进度达到 ``at`` 时，对 ``func`` 进行调用，
        可传入 ``*args`` 和 ``**kwargs``
        '''
        rough_at = round(at, 3)    # 防止因为精度误差使得本来计划更迟的任务被更早地执行了
        task = Timeline.ScheduledTask(rough_at, func, args, kwargs)
        insort(self.scheduled_tasks, task, key=lambda x: x.at)

    def timeout(self, delay: float, func: Callable, *args, **kwargs) -> None:
        '''
        相当于 `schedule(self.current_time + delay, func, *args, **kwargs)`
        '''
        self.schedule(self.current_time + delay, func, *args, **kwargs)

    # region progress

    def forward(self, dt: float = 1, *, _detect_changes=True, _record_lineno=True) -> None:
        '''
        向前推进 ``dt`` 秒
        '''
        if dt <= 0:
            raise ValueError(_('dt must be greater than 0'))

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

    def prepare(self, *anims: Animation, **kwargs) -> TimeRange:
        '''
        应用动画
        '''
        anim = AnimGroup(*anims, **kwargs)
        anim.local_range.at += self.current_time
        anim.compute_global_range(anim.local_range.at, anim.local_range.duration)

        anim.anim_pre_init()
        self.detect_changes_of_all()
        anim.anim_init()

        self.anims.append(anim)

        return anim.local_range

    def play(self, *anims: Animation, **kwargs) -> TimeRange:
        '''
        应用动画并推进到动画结束的时候
        '''
        t_range = self.prepare(*anims, **kwargs)
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
        - 在 GUI 界面中，可以使用 ``Ctrl+Z`` 快速移动到前一个暂停点，``Ctrl+C`` 快速移动到后一个
        '''
        self.pause_points.append(Timeline.PausePoint(self.current_time + offset, at_previous_frame))

    # endregion

    # region display

    def is_displaying(self, item: Item) -> None:
        '''
        判断特定的物件是否正在显示中

        另见：:meth:`show`、:meth:`hide`
        '''
        return item in self.item_display_times

    def _show(self, item: Item) -> None:
        self.item_display_times.setdefault(item, self.current_time)

    def show(self, *roots: Item, root_only=False) -> None:
        '''
        显示物件
        '''
        for root in roots:
            for item in root.walk_self_and_descendants(root_only):
                self._show(item)
                self.track(item)

    def _hide(self, item: Item) -> Display:
        time = self.item_display_times.pop(item, None)
        if time is None:
            return

        duration = self.current_time - time

        anim = Display(item, duration=duration)
        anim.local_range.at += time
        anim.compute_global_range(anim.local_range.at, anim.local_range.duration)
        self.display_anims.append(anim)
        return anim

    def hide(self, *roots: Item, root_only=False) -> None:
        '''
        隐藏物件
        '''
        for root in roots:
            for item in root.walk_self_and_descendants(root_only):
                self._hide(item)

    def cleanup_display(self) -> None:
        '''
        对目前显示中的所有物件调用隐藏，使得正确产生 :class:`~.Display` 对象
        '''
        for item in list(self.item_display_times.keys()):
            self._hide(item)

    # endregion

    # region audio_and_subtitle

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

        info = Timeline.PlayAudioInfo(audio,
                                      TimeRange(self.current_time + delay, duration),
                                      TimeRange(begin, duration))
        self.audio_infos.append(info)

        return info.range.copy()

    def has_audio(self) -> bool:
        '''
        是否有可以播放的音频
        '''
        return len(self.audio_infos) != 0

    def get_audio_samples_of_frame(
        self,
        fps: float,
        framerate: int,
        frame: int
    ) -> np.ndarray:
        '''
        提取特定帧的音频流
        '''
        begin = frame / fps
        end = (frame + 1) / fps
        channels = self.config_getter.audio_channels

        output_sample_count = math.floor(end * framerate) - math.floor(begin * framerate)
        if channels == 1:
            result = np.zeros(output_sample_count, dtype=np.int16)
        else:
            result = np.zeros((output_sample_count, channels), dtype=np.int16)

        for info in self.audio_infos:
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
                if channels == 1:
                    data = np.concatenate([
                        np.zeros(left_blank, dtype=np.int16),
                        data,
                        np.zeros(right_blank, dtype=np.int16)
                    ])
                else:
                    # channels = data.shape[1]
                    data = np.concatenate([
                        np.zeros((left_blank, channels), dtype=np.int16),
                        data,
                        np.zeros((right_blank, channels), dtype=np.int16)
                    ])

            result += resize_preserving_order(data, output_sample_count)

        return result

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
            range = TimeRange(self.current_time + delay, duration)

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

    # endregion

    # region history

    def track(self, item: Item) -> None:
        '''
        使得 ``item`` 在每次 ``forward`` 和 ``play`` 时都会被自动调用 :meth:`~.Item.detect_change`
        '''
        self.items_history[item]

    def track_item_and_descendants(self, item: Item, *, root_only: bool = False) -> None:
        '''
        相当于对 ``item`` 及其所有的后代物件调用 :meth:`track`
        '''
        for subitem in item.walk_self_and_descendants(root_only):
            self.items_history[subitem]

    def detect_changes_of_all(self) -> None:
        '''
        检查所有物件是否有产生变化并记录
        '''
        for item, ih in self.items_history.items():
            self._detect_change(item, ih, as_time=self.current_time)

    def detect_changes(self, items: Iterable[Item], *, as_time: float | None = None) -> None:
        '''
        检查指定的列表中的物件是否有产生变化并记录（仅检查自身而不包括子物件的）
        '''
        if as_time is None:
            as_time = self.current_time
        for item in items:
            self._detect_change(item, self.items_history[item], as_time=as_time)

    @staticmethod
    def _detect_change(item: Item, ih: ItemHistory, *, as_time: float) -> None:
        history_wo_dnmc = ih.history_without_dynamic
        if not history_wo_dnmc.has_record() or not history_wo_dnmc.latest().data.not_changed(item):
            item_copy = item.store()
            ih.history.record_as_time(as_time, item_copy)
            history_wo_dnmc.record_as_time(as_time, item_copy)

    def register_dynamic(
        self,
        item: Item,
        dynamic: DynamicItem,
        static: Item | None,
        begin: float,
        end: float,
        static_replaceable: bool
    ) -> None:
        ih = self.items_history[item]
        ih.history.record_as_time(begin, dynamic)

        if static is None:
            if ih.history_without_dynamic.has_record():
                static = ih.history_without_dynamic.latest().data
            else:
                static = item.store()
        ih.history.record_as_time(end, static, replaceable=static_replaceable)
        ih.history_without_dynamic.record_as_time(end, static, replaceable=static_replaceable)

    def item_current[T](self, item: T, *, as_time: float | None = None, skip_dynamic=False) -> T:
        '''
        另见 :meth:`~.Item.current`
        '''
        ih = self.items_history[item]
        history = ih.history_without_dynamic if skip_dynamic else ih.history
        if not history.has_record():
            return item

        if as_time is None:
            params = updater_params_ctx.get(None)
            if params is not None:
                as_time = params.global_t
        if as_time is None:
            as_time = Animation.global_t_ctx.get(None)

        if as_time is None:
            return item

        item_or_dynamic = history.get(as_time)
        return item_or_dynamic if isinstance(item_or_dynamic, Item) else item_or_dynamic(as_time)

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
        times_of_code = self.times_of_code
        if not times_of_code:
            return -1

        idx = bisect(times_of_code, time, key=lambda x: x.time)
        idx = clip(idx, 0, len(times_of_code) - 1)
        return times_of_code[idx].line

    # endregion

    # region debug

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

        log.debug(f't={time}  {ext_msg}at construct.{self.get_construct_lineno()}')

    # endregion


class SourceTimeline(Timeline):     # pragma: no cover
    '''
    与 :class:`Timeline` 相比，会在背景显示源代码
    '''
    def build(self, *, quiet=False) -> TimelineAnim:
        from janim.items.text.text import SourceDisplayer
        with ContextSetter(self.ctx_var, self), self.with_config():
            SourceDisplayer(self.__class__, depth=10000).show()
        return super().build(quiet=quiet)


SEGMENT_DURATION = 10


class _LongOptAnimGroup(AnimGroup):
    '''
    对含有较多物件、持续时间长的情况进行了优化的 :class:`~.AnimGroup`
    '''
    def init_segments(self) -> None:
        left = math.floor(self.global_range.at / SEGMENT_DURATION)
        right = math.ceil(self.global_range.end / SEGMENT_DURATION)
        count = right - left + 1

        self.segment_left = left
        self.segments: list[list[Animation]] = [[] for _ in range(count)]

        for anim in self.anims:
            anim_left = math.floor(anim.global_range.at / SEGMENT_DURATION)
            anim_right = math.ceil(anim.global_range.end / SEGMENT_DURATION)

            for idx in range(anim_left - left, anim_right - left):
                self.segments[idx].append(anim)

    def anim_on_alpha(self, alpha: float) -> None:
        global_t = self.global_t_ctx.get()

        idx = math.floor(global_t / SEGMENT_DURATION)
        for anim in self.segments[idx]:
            anim_t = self.get_anim_t(alpha, anim)
            if anim.is_visible(global_t):
                anim.anim_on(anim_t)


class TimelineAnim(AnimGroup):
    '''
    运行 :meth:`Timeline.build` 后返回的动画组

    - ``self.display_anim`` 是由 :meth:`Timeline.construct` 中执行
      :meth:`Timeline.show` 和 :meth:`Timeline.hide` 而产生的
    - ``self.user_anim`` 是显式使用了 :meth:`Timeline.prepare` 或 :meth:`Timeline.play` 而产生的
    '''
    def __init__(self, timeline: Timeline, **kwargs):
        self.display_anim = _LongOptAnimGroup(*timeline.display_anims)
        self.user_anim = _LongOptAnimGroup(*timeline.anims)
        super().__init__(self.display_anim, self.user_anim, **kwargs)
        self.maxt = self.local_range.duration = timeline.current_time

        self.display_anim.global_range = self.display_anim.local_range
        self.user_anim.global_range = self.user_anim.local_range
        self.global_range = self.local_range

        for group in (self.display_anim, self.user_anim):
            group.init_segments()

        # 按照每 10s 切分区段
        segment_count = math.ceil(self.global_range.duration / SEGMENT_DURATION) + 1
        self.segments: list[list[Animation]] = [[] for _ in range(segment_count)]
        for anim in self.flatten():
            left = math.floor(anim.global_range.at / SEGMENT_DURATION)
            right = math.ceil(anim.global_range.end / SEGMENT_DURATION)
            for idx in range(left, right):
                self.segments[idx].append(anim)

        self._time: float | None = None

    @property
    def cfg(self) -> Config | ConfigGetter:
        return self.timeline.config_getter

    def current_camera_info(self) -> CameraInfo:
        return self.timeline.camera.current(as_time=self._time).points.info

    def anim_on(self, local_t: float) -> None:
        # 使最后一帧不空屏
        if np.isclose(local_t, self.global_range.duration):
            local_t -= 1 / self.cfg.fps

        self._time = local_t
        with ContextSetter(self.global_t_ctx, local_t):
            super().anim_on(local_t)

    def render_all(self, ctx: mgl.Context) -> None:
        '''
        调用所有的 :class:`RenderCall` 进行渲染
        '''
        if self._time is None:
            return

        try:
            with ContextSetter(Animation.global_t_ctx, self._time), \
                 ContextSetter(Timeline.ctx_var, self.timeline),    \
                 self.timeline.with_config():
                timeline = self.timeline
                camera_info = timeline.camera.current().points.info
                anti_alias_radius = self.cfg.anti_alias_width / 2 * camera_info.scaled_factor

                set_global_uniforms(
                    ctx,
                    ('JA_CAMERA_SCALED_FACTOR', camera_info.scaled_factor),
                    ('JA_VIEW_MATRIX', camera_info.view_matrix.T.flatten()),
                    ('JA_FIXED_DIST_FROM_PLANE', camera_info.fixed_distance_from_plane),
                    ('JA_PROJ_MATRIX', camera_info.proj_matrix.T.flatten()),
                    ('JA_FRAME_RADIUS', camera_info.frame_radius),
                    ('JA_ANTI_ALIAS_RADIUS', anti_alias_radius)
                )

                with ContextSetter(Renderer.data_ctx, RenderData(ctx=ctx,
                                                                 camera_info=camera_info,
                                                                 anti_alias_radius=anti_alias_radius)):
                    idx = math.floor(self._time / SEGMENT_DURATION)
                    # 使用 heapq 以深度为序调用 RenderCall
                    render_calls = heapq.merge(
                        *[
                            anim.render_call_list
                            for anim in self.segments[idx]
                            if anim.render_call_list and anim.is_visible(self._time)
                        ],
                        key=lambda x: x.depth,
                        reverse=True
                    )
                    for render_call in render_calls:
                        render_call.func()

        except Exception:
            traceback.print_exc()

    capture_ctx: mgl.Context | None = None
    capture_fbo: mgl.Framebuffer | None = None

    def capture(self) -> Image.Image:
        if TimelineAnim.capture_ctx is None:
            TimelineAnim.capture_ctx = mgl.create_standalone_context(require=430)
            TimelineAnim.capture_ctx.enable(mgl.BLEND)
            TimelineAnim.capture_ctx.blend_func = (
                mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA,
                mgl.ONE, mgl.ONE
            )
            TimelineAnim.capture_ctx.blend_equation = mgl.FUNC_ADD, mgl.MAX

            pw, ph = self.cfg.pixel_width, self.cfg.pixel_height
            TimelineAnim.capture_fbo = TimelineAnim.capture_ctx.framebuffer(
                color_attachments=TimelineAnim.capture_ctx.texture(
                    (pw, ph),
                    components=4,
                    samples=0,
                ),
                depth_attachment=TimelineAnim.capture_ctx.depth_renderbuffer(
                    (pw, ph),
                    samples=0
                )
            )

        fbo = TimelineAnim.capture_fbo
        fbo.use()
        fbo.clear(*self.cfg.background_color.rgb)
        self.render_all(TimelineAnim.capture_ctx)

        return Image.frombytes(
            "RGBA", fbo.size, fbo.read(components=4),
            "raw", "RGBA", 0, -1
        )
