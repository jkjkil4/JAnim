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
from typing import TYPE_CHECKING, Callable, Iterable

import moderngl as mgl

from janim.anims.animation import Animation, TimeRange
from janim.anims.composition import AnimGroup
from janim.anims.display import Display
from janim.anims.transform import MethodTransform
from janim.camera.camera import Camera
from janim.exception import (StoreFailedError, StoreNotFoundError,
                             TimelineLookupError)
from janim.items.item import Item
from janim.logger import log
from janim.render.base import RenderData, Renderer, set_global_uniforms
from janim.utils.config import Config
from janim.utils.simple_functions import clip

if TYPE_CHECKING:   # pragma: no cover
    from janim.items.item import Item

GET_DATA_DELTA = 1e-5
ANIM_END_DELTA = 1e-5 * 2
DEFAULT_DURATION = 1

type DynamicData = Callable[[float], Item.Data]


class Timeline(metaclass=ABCMeta):
    '''
    继承该类并实现 :meth:`construct` 方法，以实现动画的构建逻辑

    调用 :meth:`build` 可以得到构建完成的动画对象
    '''

    ctx_var: ContextVar[Timeline] = ContextVar('Timeline.ctx_var', default=None)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_time: float = 0
        self.times_of_code: list[Timeline.TimeOfCode] = []

        self.scheduled_tasks: list[Timeline.ScheduledTask] = []
        self.anims: list[AnimGroup] = []
        self.display_anims: list[Display] = []

        self.item_stored_datas: defaultdict[Item, list[Timeline.TimedItemData]] = defaultdict(list)
        self.item_display_times: dict[Item, int] = {}

        self.camera = Camera()
        self.register(self.camera)

    @abstractmethod
    def construct(self) -> None:
        '''
        继承该方法以实现动画的构建逻辑
        '''
        pass

    def build(self, *, quiet=False) -> TimelineAnim:
        '''
        构建动画并返回
        '''
        token = self.ctx_var.set(self)
        try:
            self._build_frame = inspect.currentframe()

            if not quiet:
                log.info(f'Building "{self.__class__.__name__}"')
                start_time = time.time()

            self.construct()

            if self.current_time == 0:
                self.forward(DEFAULT_DURATION)  # 使得没有任何前进时，产生一点时间，避免除零以及其它问题
                log.info(f'"{self.__class__.__name__}" 构建后没有产生时长，自动产生了 {DEFAULT_DURATION}s 的时长')
            self.cleanup_display(trail=2 / Config.get.fps)
            global_anim = TimelineAnim(self)

            if not quiet:
                elapsed = time.time() - start_time
                log.info(f'Finished building "{self.__class__.__name__}" in {elapsed:.2f} s')

        finally:
            self.ctx_var.reset(token)

        return global_anim

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

    def prepare(self, *anims: Animation, **kwargs) -> TimeRange:
        '''
        应用动画
        '''
        anim = AnimGroup(*anims, **kwargs)
        anim.local_range.at += self.current_time
        anim.set_global_range(anim.local_range.at, anim.local_range.duration)

        anim.anim_pre_init()
        self.detect_changes_of_all()
        anim.anim_init()

        self.anims.append(anim)

        return anim.local_range

    def play(self, *anims: Animation, **kwargs) -> None:
        '''
        应用动画并推进到动画结束的时候
        '''
        anims = [
            (anim.anim if isinstance(anim, MethodTransform._FakeCmpt) else anim)
            for anim in anims
        ]
        t_range = self.prepare(*anims, **kwargs)
        self.forward_to(t_range.end, _detect_changes=False)

    def schedule(self, at: float, func: Callable, *args, **kwargs) -> None:
        '''
        计划执行

        会在进度达到 ``at`` 时，对 ``func`` 进行调用，
        可传入 ``*args`` 和 ``**kwargs``
        '''
        insort(self.scheduled_tasks, Timeline.ScheduledTask(at, func, args, kwargs), key=lambda x: x.at)

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

    def get_lineno_at_time(self, time: float):
        times_of_code = self.times_of_code
        if not times_of_code:
            return -1

        idx = bisect(times_of_code, time, key=lambda x: x.time)
        idx = clip(idx, 0, len(times_of_code) - 1)
        return times_of_code[idx].line

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

        assert False

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

    def _hide(self, item: Item, *, trail=0) -> Display:
        time = self.item_display_times.pop(item, None)
        if time is None:
            return

        duration = self.current_time - time

        anim = Display(item, duration=duration + trail, root_only=True)
        anim.local_range.at += time
        anim.set_global_range(anim.local_range.at, anim.local_range.duration)
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

    def cleanup_display(self, trail=0) -> None:
        '''
        对目前显示中的所有物件调用隐藏，使得正确产生 :class:`~.Display` 对象

        ``trail`` 参数在 :meth:`build` 调用的最后使用到，以便使得最后的一帧也能看到物件
        '''
        for item in list(self.item_display_times.keys()):
            self._hide(item, trail=trail)

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


class TimelineAnim(AnimGroup):
    '''
    :class:`Timeline` 运行 :meth:`Timeline.run` 后返回的动画组

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
