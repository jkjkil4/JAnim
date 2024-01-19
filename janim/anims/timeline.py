from __future__ import annotations

import inspect
import math
from abc import ABCMeta, abstractmethod
from bisect import insort
from contextvars import ContextVar
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, Callable, Self

from janim.anims.animation import TimeRange
from janim.anims.display import Display
from janim.anims.composition import AnimGroup
from janim.logger import log

if TYPE_CHECKING:   # pragma: no cover
    from janim.anims.animation import Animation
    from janim.items.item import Item


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
            raise LookupError(f'{f_back.f_code.co_qualname} 无法在 Timeline.construct 之外使用')
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
        data: Item.Data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_time: float = 0
        self.times_of_code: list[Timeline.TimeOfCode] = []

        self.scheduled_tasks: list[Timeline.ScheduledTask] = []
        self.anims: list[Animation] = []

        self.item_stored_datas: defaultdict[Item, list[Timeline.TimedItemData]] = defaultdict(list)
        self.item_display_times: dict[Item, int] = {}

    @abstractmethod
    def construct(self) -> None:
        '''
        继承该方法以实现动画的构建逻辑
        '''
        pass

    def build(self) -> AnimGroup:
        '''
        构建动画并返回
        '''
        token = self.ctx_var.set(self)
        try:
            self._build_frame = inspect.currentframe()
            self.construct()
            self.cleanup_display()
            self.global_anim = AnimGroup(*self.anims)
        finally:
            self.ctx_var.reset(token)

        return self.global_anim

    def register(self, item: Item) -> None:
        '''
        在 :meth:`construct` 中创建的物件会自动调用该方法
        '''
        self.item_stored_datas[item]

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

    def forward(self, dt: float, *, _detect_changes=True) -> None:
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
        self.detect_changes_of_all()

        anim = AnimGroup(*anims, **kwargs)
        anim.set_global_range(self.current_time + anim.local_range.at)
        self.anims.append(anim)

        return anim.global_range

    def play(self, *anims: Animation, **kwargs) -> None:
        '''
        应用动画并推进到动画结束的时候
        '''
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
            self._detect_change(item, datas)

    def detect_changes(self, items: Iterable[Item]) -> None:
        '''
        检查指定的列表中的物件是否有产生变化并记录（仅检查自身而不包括子物件的）
        '''
        for item in items:
            self._detect_change(item, self.item_stored_datas[item])

    def _detect_change(
        self,
        item: Item,
        datas: list[Timeline.TimedItemData],
    ) -> None:
        if not datas:
            datas.append(Timeline.TimedItemData(0, item.store_data()))

        elif datas[-1].data.is_changed():
            if self.current_time < datas[-1].time:
                # TOOD: 明确是什么物件
                raise RuntimeError('记录物件数据失败，可能是因为物件处于动画中')

            elif self.current_time == datas[-1].time:
                datas[-1].data = item.store_data()

            else:  # as_time > datas[-1].time
                datas.append(Timeline.TimedItemData(self.current_time, item.store_data()))

    def _get_stored_data_at_time(self, item: Item, t: float) -> Item.Data:
        # TODO: optimize
        datas = self.item_stored_datas[item]

        if not datas:
            raise ValueError('Not stored')

        for timed_data in reversed(datas):
            if timed_data.time <= t:
                return timed_data.data

        assert False

    def get_stored_data_at_right(self, item: Item, t: float) -> Item.Data:
        '''
        得到在指定时间之前的瞬间，物件的数据
        '''
        return self._get_stored_data_at_time(item, t + 1e-5)

    def get_stored_data_at_left(self, item: Item, t: float) -> Item.Data:
        '''
        得到在指定时间之后的瞬间，物件的数据
        '''
        return self._get_stored_data_at_time(item, t - 1e-5)

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

    def _hide(self, item: Item) -> None:
        time = self.item_display_times.pop(item, None)
        if time is None:
            return

        duration = self.current_time - time

        anim = Display(item, duration=duration, root_only=True)
        anim.set_global_range(time)
        self.anims.append(anim)

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

        log.debug(f't={time}  {ext_msg}at build.{self.get_construct_lineno()}')

    def dbg_item_builder(self, item: Item):     # pragma: no cover
        return Timeline._DbgItemBuilder(self, item)

    class _DbgItemBuilder:   # pragma: no cover
        def __init__(self, timeline: Timeline, item: Item):
            self.timeline = timeline
            self.item = item

            self.cmpt_formatters: dict[type, Callable] = {}

        def cmpt[T](self, cls: type[T], formatter: Callable[[T]]) -> Self:
            self.cmpt_formatters[cls] = formatter
            return self

        def show(self) -> None:
            lines = []

            lines.append('======')
            lines.append(f'{self.item.__class__.__name__} {id(self.item):X}')
            lines.append('======')
            for timed_data in self.timeline.item_stored_datas[self.item]:
                time = Timeline.fmt_time(timed_data.time)
                lines.append(f'- Time={time}')

                for key, cmpt in timed_data.data.components.items():
                    formatter = self.cmpt_formatters.get(cmpt.__class__, None)
                    if formatter is None:
                        continue

                    pre = f'  {key}= '

                    ret = str(formatter(cmpt))
                    ret = ('\n' + ' ' * len(pre)).join(ret.splitlines())

                    lines.append(f'{pre}{ret}')

            log.debug('\n'.join(lines))

    # endregion
