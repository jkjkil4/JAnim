from __future__ import annotations

import inspect
import math
import time
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from contextvars import ContextVar
from typing import Iterable, Self

from janim.anims.anim_stack import AnimStack
from janim.anims.animation_refactor import TimeAligner, TimeRange
from janim.anims.composition_refactor import AnimGroup
from janim.camera.camera import Camera
from janim.exception import TimelineLookupError
from janim.items.item_refactor import Item
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.typing import SupportsAnim
from janim.utils.config import Config, ConfigGetter, config_ctx_var
from janim.utils.data import ContextSetter

_ = get_local_strings('timeline')


class Timeline(metaclass=ABCMeta):
    '''
    继承该类并实现 :meth:`construct` 方法，以实现动画的构建逻辑

    调用 :meth:`build` 可以得到构建完成的 :class:`Timeline` 对象
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

    # TODO: TimeOfCode

    # TODO: ScheduledTask

    # TODO: PlayAudioInfo

    # TODO: SubtitleInfo

    # TODO: PausePoint

    # TODO: DEPRECATED: ItemHistory

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_time: float = 0
        # TODO: self.times_of_code

        # TODO: scheduled_tasks
        # TODO: DEPRECATED?: self.anims
        # TODO: DEPRECATED?: self.display_anims
        # TODO: audio_infos
        # TODO: subtitle_infos

        # TODO: self.pause_points

        # TODO: DEPRECATED: items_history
        # TODO: DEPRECATED?: item_display_times
        self.time_aligner: TimeAligner = TimeAligner()
        self.anim_stacks: defaultdict[Item, AnimStack] = defaultdict(lambda: AnimStack(self.time_aligner))

    @abstractmethod
    def construct(self) -> None:
        '''
        继承该方法以实现动画的构建逻辑
        '''
        pass    # pragma: no cover

    def build(self, *, quiet=False, hide_subtitles=False) -> BuiltTimeline:
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

            # TODO: if self.current_time == 0

            # TODO: cleanup_display

            # TODO: for item, ih in self.items_history.items():

            built = BuiltTimeline(self)

            if not quiet:   # pragma: no cover
                elapsed = time.time() - start_time
                log.info(
                    _('Finished building "{name}" in {elapsed:.2f} s')
                    .format(name=self.__class__.__name__, elapsed=elapsed)
                )

        return built

    # TODO: schedule

    # TODO: timeout

    # region progress

    # TODO: arg _record_lineno
    def forward(self, dt: float = 1, *, _detect_changes=True):
        '''
        向前推进 ``dt`` 秒
        '''
        if dt <= 0:
            raise ValueError(_('dt must be greater than 0'))

        if _detect_changes:
            self.detect_changes_of_all()

        to_time = self.current_time + dt

        # TODO: while self.scheduled_tasks

        self.current_time = to_time

        # TODO: if _record_lineno

    def forward_to(self, t: float, *, _detect_changes=True) -> None:
        '''
        向前推进到 ``t`` 秒的时候
        '''
        self.forward(t - self.current_time, _detect_changes=_detect_changes)

    def prepare(self, *anims: SupportsAnim, at: float = 0, **kwargs) -> TimeRange:
        self.detect_changes_of_all()
        group = AnimGroup(*anims, at=at + self.current_time, **kwargs)
        # TODO: fix float inprecise
        group._time_fixed()

    def play(self, *anims: SupportsAnim, **kwargs) -> TimeRange:
        t_range = self.prepare(*anims, **kwargs)
        self.forward_to(t_range.end, _detect_changes=False)
        return t_range

    # TODO: pause_point

    # endregion

    # TODO: region display

    # TODO: region audio_and_subtitle

    # region direct-modifier

    def track(self, item: Item) -> None:
        '''
        使得 ``item`` 在每次 ``forward`` 和 ``play`` 时都会被自动调用 :meth:`~.Item.detect_change`
        '''
        self.anim_stacks[item]

    def track_item_and_descendants(self, item: Item, *, root_only: bool = False) -> None:
        '''
        相当于对 ``item`` 及其所有的后代物件调用 :meth:`track`
        '''
        for subitem in item.walk_self_and_descendants(root_only):
            self.anim_stacks[subitem]

    def detect_changes_of_all(self) -> None:
        '''
        检查物件的变化并将变化记录为 :class:`DirectModifier`
        '''
        for item, stack in self.anim_stacks.items():
            stack.detect_change(item, self.current_time)

    def detect_changes(self, items: Iterable[Item]) -> None:
        '''
        检查指定的列表中物件的变化，并将变化记录为 :class:`DirectModifier`

        （仅检查自身而不包括子物件的）
        '''
        for item in items:
            self.anim_stacks[item].detect_change(item, self.current_time)

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

    # TODO: get_lineno_of_time

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


# TODO: SourceTimeline


# TODO: SEGMENT_DURATION


# TODO: _LongOptAnimGroup


class BuiltTimeline:
    '''
    运行 :meth:`Timeline.build` 后返回的实例
    '''
    def __init__(self, timeline: Timeline):
        self.timeline = timeline

    @property
    def cfg(self) -> Config | ConfigGetter:
        return self.timeline.config_getter

    # TODO: anim_on

    # TODO: render_all

    # TODO: capture
