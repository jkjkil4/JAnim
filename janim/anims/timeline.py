from __future__ import annotations

import heapq
import inspect
import math
import time
import traceback
from abc import ABCMeta, abstractmethod
from bisect import bisect, insort
from collections import defaultdict
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable, Iterable, Self

import moderngl as mgl
import numpy as np

from janim.anims.animation import Animation, TimeRange
from janim.anims.composition import AnimGroup
from janim.anims.display import Display
from janim.camera.camera import Camera
from janim.constants import DOWN, UP
from janim.exception import (NotAnimationError, StoreFailedError,
                             StoreNotFoundError, TimelineLookupError)
from janim.items.audio import Audio
from janim.items.item import Item
from janim.items.svg.typst import TypstText
from janim.items.text.text import Text
from janim.logger import log
from janim.render.base import RenderData, Renderer, set_global_uniforms
from janim.utils.config import Config
from janim.utils.iterables import resize_preserving_order
from janim.utils.simple_functions import clip

GET_DATA_DELTA = 1e-5
ANIM_END_DELTA = 1e-5 * 2
DEFAULT_DURATION = 1

type DynamicData = Callable[[float], Item.Data]


class Timeline(metaclass=ABCMeta):
    '''
    继承该类并实现 :meth:`construct` 方法，以实现动画的构建逻辑

    调用 :meth:`build` 可以得到构建完成的动画对象
    '''

    # region context

    ctx_var: ContextVar[Timeline | None] = ContextVar('Timeline.ctx_var', default=None)

    @staticmethod
    def get_context(raise_exc=True) -> Timeline | None:
        '''
        调用该方法可以得到当前正在构建的 :class:`Timeline` 对象

        - 如果在 :meth:`construct` 方法外调用，且 ``raise_exc=True`` （默认），则抛出 ``LookupError``
        '''
        obj = Timeline.ctx_var.get(None)
        if obj is None and raise_exc:
            f_back = inspect.currentframe().f_back
            raise TimelineLookupError(f'{f_back.f_code.co_qualname} 无法在 Timeline.construct 之外使用')
        return obj

    class CtxBlocker:
        '''
        使得在 ``with Timeline.CtxBlocker():`` 内，物件不会自动调用 :meth:`register`

        用于临时创建物件时
        '''
        def __enter__(self) -> Self:
            self.token = Timeline.ctx_var.set(None)

        def __exit__(self, exc_type, exc_value, tb):
            Timeline.ctx_var.reset(self.token)

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
    class TimedItemData:
        '''
        表示从 ``time`` 之后，物件的数据
        '''
        time: float
        data: Item.Data | DynamicData
        '''
        - 当 ``data`` 的类型为 ``Item.Data`` 时，为静态数据
        - 否则，对于 ``DynamicData`` ，会在获取时调用以得到对应数据
        '''

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_time: float = 0
        self.times_of_code: list[Timeline.TimeOfCode] = []

        self.scheduled_tasks: list[Timeline.ScheduledTask] = []
        self.anims: list[AnimGroup] = []
        self.display_anims: list[Display] = []
        self.audio_infos: list[Timeline.PlayAudioInfo] = []
        self.subtitle_infos: list[Timeline.SubtitleInfo] = []   # helpful for extracting subtitles

        self.item_stored_datas: defaultdict[Item, list[Timeline.TimedItemData]] = defaultdict(list)
        self.item_display_times: dict[Item, int] = {}

        self.camera = Camera()
        self.register(self.camera)

    @abstractmethod
    def construct(self) -> None:
        '''
        继承该方法以实现动画的构建逻辑
        '''
        pass    # pragma: no cover

    def build(self, *, quiet=False) -> TimelineAnim:
        '''
        构建动画并返回
        '''
        token = self.ctx_var.set(self)
        try:
            self._build_frame = inspect.currentframe()

            if not quiet:   # pragma: no cover
                log.info(f'Building "{self.__class__.__name__}"')
                start_time = time.time()

            self.construct()

            if self.current_time == 0:
                self.forward(DEFAULT_DURATION)  # 使得没有任何前进时，产生一点时间，避免除零以及其它问题
                if not quiet:   # pragma: no cover
                    log.info(f'"{self.__class__.__name__}" 构建后没有产生时长，自动产生了 {DEFAULT_DURATION}s 的时长')
            self.cleanup_display()
            global_anim = TimelineAnim(self)

            if not quiet:   # pragma: no cover
                elapsed = time.time() - start_time
                log.info(f'Finished building "{self.__class__.__name__}" in {elapsed:.2f} s')

        finally:
            self.ctx_var.reset(token)

        return global_anim

    def schedule(self, at: float, func: Callable, *args, **kwargs) -> None:
        '''
        计划执行

        会在进度达到 ``at`` 时，对 ``func`` 进行调用，
        可传入 ``*args`` 和 ``**kwargs``
        '''
        insort(self.scheduled_tasks, Timeline.ScheduledTask(at, func, args, kwargs), key=lambda x: x.at)

    # region progress

    def forward(self, dt: float = 1, *, _detect_changes=True) -> None:
        '''
        向前推进 ``dt`` 秒
        '''
        if dt <= 0:
            raise ValueError('dt 必须大于 0')

        if _detect_changes:
            self.detect_changes_of_all()

        to_time = self.current_time + dt

        while self.scheduled_tasks and self.scheduled_tasks[0].at <= to_time:
            task = self.scheduled_tasks.pop(0)
            self.current_time = task.at
            task.func(*task.args, **task.kwargs)

        self.current_time = to_time

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

    @staticmethod
    def _get_anim_object(anim) -> Animation:
        attr = getattr(anim, '__anim__', None)
        if attr is not None and callable(attr):
            return attr()
        return anim

    def prepare(self, *anims: Animation, **kwargs) -> TimeRange:
        '''
        应用动画
        '''
        anims = [
            self._get_anim_object(anim)
            for anim in anims
        ]
        for anim in anims:
            if not isinstance(anim, Animation):
                raise NotAnimationError('传入了非动画对象，可能是你忘记使用 .anim 了')

        anim = AnimGroup(*anims, **kwargs)
        anim.local_range.at += self.current_time
        anim.compute_global_range(anim.local_range.at, anim.local_range.duration)

        anim.anim_pre_init()
        self.detect_changes_of_all()
        anim.anim_init()

        self.anims.append(anim)

        return anim.local_range

    def play(self, *anims: Animation, **kwargs) -> None:
        '''
        应用动画并推进到动画结束的时候
        '''
        t_range = self.prepare(*anims, **kwargs)
        self.forward_to(t_range.end, _detect_changes=False)

    # endregion

    # region display

    def is_displaying(self, item: Item) -> None:
        return item in self.item_display_times

    def _show(self, item: Item) -> None:
        self.item_display_times.setdefault(item, self.current_time)

    def show(self, *roots: Item, root_only=False) -> None:
        '''
        显示物件
        '''
        for root in roots:
            self._show(root)
            if not root_only:
                for item in root.descendants():
                    self._show(item)

    def _hide(self, item: Item) -> Display:
        time = self.item_display_times.pop(item, None)
        if time is None:
            return

        duration = self.current_time - time

        anim = Display(item, duration=duration, root_only=True)
        anim.local_range.at += time
        anim.compute_global_range(anim.local_range.at, anim.local_range.duration)
        self.display_anims.append(anim)
        return anim

    def hide(self, *roots: Item, root_only=False) -> None:
        '''
        隐藏物件
        '''
        for root in roots:
            self._hide(root)
            if not root_only:
                for item in root.descendants():
                    self._hide(item)

    def cleanup_display(self) -> None:
        '''
        对目前显示中的所有物件调用隐藏，使得正确产生 :class:`~.Display` 对象
        '''
        for item in list(self.item_display_times.keys()):
            self._hide(item)

    # endregion

    # region audio

    def play_audio(
        self,
        audio: Audio,
        *,
        delay: float = 0,
        begin: float = 0,
        end: float = -1,
    ) -> TimeRange:
        '''
        在当前位置播放音频

        - 可以指定 ``begin`` 和 ``end`` 表示裁剪区段
        - 可以指定在当前位置往后 ``delay`` 秒才开始播放

        返回值表示播放的时间段
        '''
        if end == -1:
            end = audio.duration()
        duration = end - begin

        info = Timeline.PlayAudioInfo(audio,
                                      TimeRange(self.current_time + delay, duration),
                                      TimeRange(begin, duration))
        self.audio_infos.append(info)

        return info.range.copy()

    def has_audio(self) -> bool:
        return len(self.audio_infos) != 0

    def get_audio_samples_of_frame(
        self,
        fps: float,
        framerate: int,
        frame: int
    ) -> np.ndarray:
        begin = frame / fps
        end = (frame + 1) / fps

        output_sample_count = math.floor(end * framerate) - math.floor(begin * framerate)
        result = np.zeros(output_sample_count, dtype=np.int16)

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

            data = audio._samples._data[max(clip_begin, frame_begin): min(clip_end, frame_end)]

            if left_blank != 0 or right_blank != 0:
                data = np.concatenate([
                    np.zeros(left_blank, dtype=np.int16),
                    data,
                    np.zeros(right_blank, dtype=np.int16)
                ])

            result += resize_preserving_order(data, output_sample_count)

        return result

    # endregion

    # region subtitle

    def subtitle(
        self,
        text: str | Iterable[str],
        delay: float = 0,
        duration: float = 1,
        scale: float | Iterable[float] = 0.8,
        use_typst_text: bool | Iterable[bool] = False,
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
        text_lst = [text] if isinstance(text, str) else text
        scale_lst = [scale] if not isinstance(scale, Iterable) else scale
        use_typst_lst = [use_typst_text] if not isinstance(use_typst_text, Iterable) else use_typst_text

        range = TimeRange(self.current_time + delay, duration)
        for text, scale, use_typst_text in zip(reversed(text_lst),
                                               reversed(resize_preserving_order(scale_lst, len(text_lst))),
                                               reversed(resize_preserving_order(use_typst_lst, len(text_lst)))):
            subtitle = (TypstText if use_typst_text else Text)(text, **kwargs)
            subtitle.points.scale(scale)
            self.place_subtitle(subtitle, range)
            self.subtitle_infos.append(Timeline.SubtitleInfo(text,
                                                             range,
                                                             kwargs,
                                                             subtitle))
            self.schedule(range.at, subtitle.show)
            self.schedule(range.end, subtitle.hide)

        return range.copy()

    def place_subtitle(self, subtitle: Text, range: TimeRange) -> None:
        for other in reversed(self.subtitle_infos):
            # 根据 TimelineView 中排列显示标签的经验
            # 这里加了一个 np.isclose 的判断
            # 如果不加可能导致前一个字幕消失但是后一个字幕凭空出现在更上面
            # （但是我没有测试过是否会出现这个bug，只是根据写 TimelineView 时的经验加了 np.isclose）
            if other.range.at <= range.at < other.range.end and not np.isclose(range.at, other.range.end):
                subtitle.points.next_to(other.subtitle, UP)
                return
        subtitle.points.to_border(DOWN)

    # endregion

    # region stored_data

    # region register

    def register(self, item: Item) -> None:
        '''
        在 :meth:`construct` 中创建的物件会自动调用该方法
        '''
        self.item_stored_datas[item]

    def register_dynamic_data(self, item: Item, data: DynamicData, as_time: float) -> None:
        '''
        注册动态数据信息

        表示在调用 :meth:`get_stored_data_at_time` 时，如果其时间在 ``as_time`` 和下一个数据的时间之间，
        就调用 ``data`` 来产生动态的数据

        例如，在 :class:`~.MethodTransform` 中使用到
        '''
        datas = self.item_stored_datas[item]

        # 在调用该方法前必须执行过 _detect_change，所以这里可以直接写 datas[-1]
        if as_time < datas[-1].time:
            # TOOD: 明确是什么物件
            raise StoreFailedError('记录物件数据失败，可能是因为物件处于动画中')

        datas.append(Timeline.TimedItemData(as_time, data))

    # endregion

    # region detect_change

    def detect_changes_of_all(self) -> None:
        '''
        检查所有物件是否有产生变化并记录
        '''
        for item, datas in self.item_stored_datas.items():
            self._detect_change(item, datas, as_time=self.current_time)

    def detect_changes(self, items: Iterable[Item], *, as_time: float | None = None) -> None:
        '''
        检查指定的列表中的物件是否有产生变化并记录（仅检查自身而不包括子物件的）
        '''
        if as_time is None:
            as_time = self.current_time
        for item in items:
            self._detect_change(item, self.item_stored_datas[item], as_time=as_time)

    def _detect_change(
        self,
        item: Item,
        datas: list[Timeline.TimedItemData],
        *,
        as_time: float,
    ) -> None:
        if not datas:
            datas.append(Timeline.TimedItemData(0, item.store_data()))
            return

        static = None
        for timed_data in reversed(datas):
            if isinstance(timed_data.data, Item.Data):
                static = timed_data
                break

        assert static is not None

        if static.data.is_changed():
            if as_time < datas[-1].time:
                # TOOD: 明确是什么物件
                raise StoreFailedError('记录物件数据失败，可能是因为物件处于动画中')

            datas.append(Timeline.TimedItemData(as_time, item.store_data()))

    # endregion

    # region get_stored_data

    def get_stored_data_at_time[T](self, item: T, t: float, *, skip_dynamic_data=False) -> Item.Data[T]:
        '''
        得到在指定时间物件的数据

        在两份数据的分界处请使用 :meth:`get_stored_data_at_right` 和 :meth:`get_stored_at_left` 来明确
        '''
        datas = self.item_stored_datas[item]

        if not datas:
            raise StoreNotFoundError('Not stored')

        # TODO: optimize
        for timed_data in reversed(datas):
            if timed_data.time <= t:
                if isinstance(timed_data.data, Item.Data):
                    return timed_data.data
                else:
                    if skip_dynamic_data:
                        continue
                    return timed_data.data(t)

        assert False    # pragma: no cover

    def get_stored_data_at_right[T](self, item: T, t: float, *, skip_dynamic_data=False) -> Item.Data[T]:
        '''
        得到在指定时间之后的瞬间，物件的数据
        '''
        return self.get_stored_data_at_time(item, t + GET_DATA_DELTA, skip_dynamic_data=skip_dynamic_data)

    def get_stored_data_at_left[T](self, item: T, t: float, *, skip_dynamic_data=False) -> Item.Data[T]:
        '''
        得到在指定时间之前的瞬间，物件的数据
        '''
        return self.get_stored_data_at_time(item, t - GET_DATA_DELTA, skip_dynamic_data=skip_dynamic_data)

    def t2d[T](self, item: T, t: float | None = None, *, skip_dynamic_data=False) -> Item.Data[T]:
        '''
        ``t2d`` 是 "time to data" 的简写

        - 如果 ``t`` 为 ``None``，则自动设为 :py:obj:`~.UpdaterParams.global_t` 即当前动画运行到的时间，
          用于在 :class:`~.DataUpdater` 和 :class:`~.ItemUpdater` 中简化调用
        - 等效于调用 :meth:`get_stored_data_at_right`
        '''
        if t is None:
            from janim.anims.updater import updater_params_ctx
            t = updater_params_ctx.get().global_t
        return self.get_stored_data_at_right(item, t, skip_dynamic_data=skip_dynamic_data)

    # endregion

    # endregion

    # region lineno

    def get_construct_lineno(self) -> int | None:
        '''
        得到当前在 :meth:`construct` 中执行到的行数
        '''
        frame = inspect.currentframe().f_back
        while frame is not None:
            f_back = frame.f_back

            if f_back is self._build_frame:
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
        token = self.ctx_var.set(self)
        SourceDisplayer(self.__class__).show()
        self.ctx_var.reset(token)
        return super().build(quiet=quiet)


class TimelineAnim(AnimGroup):
    '''
    运行 :meth:`Timeline.run` 后返回的动画组

    - ``self.display_anim`` 是由 :meth:`Timeline.construct` 中执行
      :meth:`Timeline.show` 和 :meth:`Timeline.hide` 而产生的
    - ``self.user_anim`` 是显式使用了 :meth:`Timeline.prepare` 或 :meth:`Timeline.play` 而产生的
    '''
    def __init__(self, timeline: Timeline, **kwargs):
        self.timeline = timeline

        self.display_anim = AnimGroup(*timeline.display_anims)
        self.user_anim = AnimGroup(*timeline.anims)
        super().__init__(self.display_anim, self.user_anim, **kwargs)
        self.maxt = self.local_range.duration = timeline.current_time

        self.display_anim.global_range = self.display_anim.local_range
        self.user_anim.global_range = self.user_anim.local_range
        self.global_range = self.local_range

        self.flattened = self.flatten()
        self._time: float | None = None

    def anim_on(self, local_t: float) -> None:
        # 使最后一帧不空屏
        if np.isclose(local_t, self.global_range.duration):
            local_t -= 1 / Config.get.fps

        self._time = local_t
        token = self.global_t_ctx.set(local_t)
        try:
            super().anim_on(local_t)
        finally:
            self.global_t_ctx.reset(token)

    def render_all(self, ctx: mgl.Context) -> None:
        '''
        调用所有的 :class:`RenderCall` 进行渲染
        '''
        if self._time is None:
            return

        timeline = self.timeline
        camera_data = timeline.get_stored_data_at_right(timeline.camera, self._time)
        camera_info = camera_data.cmpt.points.info
        anti_alias_radius = Config.get.anti_alias_width / 2 * camera_info.scaled_factor

        set_global_uniforms(
            ctx,
            ('JA_VIEW_MATRIX', camera_info.view_matrix.T.flatten()),
            ('JA_PROJ_MATRIX', camera_info.proj_matrix.T.flatten()),
            ('JA_FRAME_RADIUS', camera_info.frame_radius),
            ('JA_ANTI_ALIAS_RADIUS', anti_alias_radius)
        )

        global_t_token = Animation.global_t_ctx.set(self._time)
        render_token = Renderer.data_ctx.set(RenderData(ctx=ctx,
                                                        camera_info=camera_info,
                                                        anti_alias_radius=anti_alias_radius))

        try:
            # 使用 heapq 以深度为序调用 RenderCall
            render_calls = heapq.merge(
                *[
                    anim.render_call_list
                    for anim in self.flattened
                    if anim.render_call_list and anim.global_range.at <= self._time < anim.global_range.end
                ],
                key=lambda x: x.depth,
                reverse=True
            )
            for render_call in render_calls:
                render_call.func()

        except Exception:
            traceback.print_exc()
        finally:
            Renderer.data_ctx.reset(render_token)
            Animation.global_t_ctx.reset(global_t_token)
