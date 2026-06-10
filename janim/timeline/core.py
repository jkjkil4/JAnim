from bisect import bisect
from collections import defaultdict
from dataclasses import dataclass
from functools import partial
import inspect
import types
from typing import TYPE_CHECKING, Callable, Iterable

from janim.anims.composition import AnimGroup
from janim.anims_core.anim_stack import AnimStack
from janim.anims_core.animation import Animation
from janim.anims_core.time import TimeAligner, TimeRange
from janim.constants import DEFAULT_DURATION
from janim.items.item import Item
from janim.locale import get_translator
from janim.render.base import Renderer
from janim.typing import SupportsAnim
from janim.utils.data import SortedKeyQueue
from janim.utils.simple_functions import clip
from janim.anims.updater import updater_params_ctx

if TYPE_CHECKING:
    from janim.timeline.timeline import TimelineItem

type RenderFunc = Callable[[Item], None]
type ItemWithRenderFunc = tuple[Item, RenderFunc]

type RenderGroupReturn = list[ItemWithRenderFunc]
type RenderGroupFn = Callable[[], RenderGroupReturn]

_ = get_translator('janim.timeline.core')


@dataclass(slots=True)
class ScheduledTask:
    """
    另见 :meth:`~.TimelineBase.schedule`
    """

    at: float
    func: Callable
    args: tuple
    kwargs: dict


@dataclass
class ExtraRenderGroup:
    t_range: TimeRange
    func: RenderGroupFn
    related_items: list[Item] | None


@dataclass
class TimeOfCode:
    """
    标记 :meth:`~.Timeline.construct` 执行到的代码行数所对应的时间
    """

    time: float
    line: int


class TimelineCore:
    """
    封装了 :class:`Timeline` 的核心功能，
    会通过继承其它类来扩充成 :class:`~.Timeline` 类，
    关于扩充功能的介绍，请参考 :class:`~.Timeline` 的文档

    这只是为了 JAnim 内部代码组织的方便，并不能单独使用，
    我们使用的时候直接用 :class:`~.Timeline` 就好了
    """

    # 只是为了让它们也出现在 Timeline 的类成员中
    ScheduledTask = ScheduledTask
    ExtraRenderGroup = ExtraRenderGroup
    TimeOfCode = TimeOfCode

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 与时间信息有关的
        self.current_time: float = 0
        self.time_aligner: TimeAligner = TimeAligner()

        # 计划执行中的函数
        self.scheduled_tasks = SortedKeyQueue[float, ScheduledTask]()

        # 物件状态以及动画相关
        self.item_appearances = ItemAppearances(self.time_aligner)
        self.anim_groups: list[AnimGroup] = []  # 这个仅用于在预览界面中显示动画区段标签
        self.extra_render_groups: list[ExtraRenderGroup] = []

        # 记录 construct 代码行及对应时间
        self.times_of_code: list[TimeOfCode] = []
        self._build_frame: types.FrameType | None = (
            None  # 用于 _extract_lineno_in_construct，会在 Timeline.build 中被设置
        )

        # ==========================================
        # 其它属性

        # 该 Timeline 中包含的子 Timeline 列表
        # 注：不包括 `to_playback_control_item` 构造的
        self.subtimeline_items: list[TimelineItem] = []

        self.hide_subtitles: bool = False
        self.show_debug_notice: bool = False

    # region progress

    def forward(self, dt: float = DEFAULT_DURATION, *, _detect_changes=True, _record_lineno=True):
        """
        向前推进 ``dt`` 秒
        """
        dt = float(dt)  # 避免 numpy 类型浮点数可能导致的问题
        if dt < 0:
            raise ValueError(_("dt can't be negative"))

        if _detect_changes:
            self.detect_changes_of_all()

        to_time = self.current_time + dt

        for task in self.scheduled_tasks.pop_up_to(to_time):
            self.current_time = task.at
            task.func(*task.args, **task.kwargs)

        self.current_time = to_time

        if _record_lineno:
            self.times_of_code.append(
                TimeOfCode(
                    self.current_time,
                    self._extract_lineno_in_construct() or -1,
                )
            )

    def forward_to(self, t: float, *, _detect_changes=True) -> None:
        """
        向前推进到 ``t`` 秒的时候
        """
        self.forward(t - self.current_time, _detect_changes=_detect_changes)

    def prepare(
        self,
        *anims: SupportsAnim,
        at: float = 0,
        name: str | None = 'prepare',
        **kwargs,
    ) -> TimeRange:
        self.detect_changes_of_all()
        group = AnimGroup(*anims, at=at + self.current_time, name=name, **kwargs)
        group.finalize()
        # 这里的 anim_groups.append 和 AnimStack.append 是不同的，后者已在 finalize 中被调用
        self.anim_groups.append(group)
        return group.t_range

    def play(
        self,
        *anims: SupportsAnim,
        name: str | None = 'play',
        **kwargs,
    ) -> TimeRange:
        t_range = self.prepare(*anims, name=name, **kwargs)
        self.forward_to(t_range.end, _detect_changes=False)  # type: ignore
        return t_range

    # endregion

    # region schedule

    def schedule(self, at: float, func: Callable, *args, **kwargs) -> None:
        """
        计划执行

        会在进度达到 ``at`` 时，对 ``func`` 进行调用，
        可传入 ``*args`` 和 ``**kwargs``
        """
        at = self.time_aligner.align_and_record(at)
        task = ScheduledTask(at, func, args, kwargs)
        self.scheduled_tasks.insert(at, task)

    def schedule_and_detect_changes(self, at: float, func: Callable, *args, **kwargs) -> None:
        """
        与 :meth:`schedule` 类似，但是在调用 ``func`` 后会记录变化的物件的状态
        """

        def wrapper(*args, **kwargs) -> None:
            func(*args, **kwargs)
            self.detect_changes_of_all()

        self.schedule(at, wrapper, *args, **kwargs)

    def timeout(self, delay: float, func: Callable, *args, **kwargs) -> None:
        """
        相当于 ``schedule(self.current_time + delay, func, *args, **kwargs)``
        """
        self.schedule(self.current_time + delay, func, *args, **kwargs)

    def timeout_and_detect_changes(self, delay: float, func: Callable, *args, **kwargs) -> None:
        """
        与 :meth:`timeout` 类似，但是在调用 ``func`` 后会记录变化的物件的状态
        """

        def wrapper(*args, **kwargs) -> None:
            func(*args, **kwargs)
            self.detect_changes_of_all()

        self.timeout(delay, wrapper, *args, **kwargs)

    # endregion

    # region ItemAppearance.stack

    def track(self, item: Item) -> None:
        """
        使得 ``item`` 在每次 ``forward`` 和 ``play`` 时都会被自动调用 :meth:`~.Item.detect_change`
        """
        self.item_appearances[item]

    def track_item_and_descendants(self, item: Item, *, root_only: bool = False) -> None:
        """
        相当于对 ``item`` 及其所有的后代物件调用 :meth:`track`
        """
        for subitem in item.walk_self_and_descendants(root_only):
            self.item_appearances[subitem]

    def detect_changes_of_all(self) -> None:
        """
        检查物件的变化并将变化记录为 :class:`~.Display`
        """
        for appr in self.item_appearances.values():
            appr.stack.detect_change(self.current_time)

    def detect_changes(self, items: Iterable[Item]) -> None:
        """
        检查指定的列表中物件的变化，并将变化记录为 :class:`~.Display`

        （仅检查自身而不包括后代物件的）
        """
        for item in items:
            self.item_appearances[item].stack.detect_change(self.current_time)

    def compute_item[T: Item](self, item: T, as_time: float, readonly: bool) -> T:
        """
        另见 :meth:`~.AnimStack.compute`
        """
        return self.item_appearances[item].stack.compute(as_time, readonly)  # type: ignore

    def item_current[T: Item](
        self, item: T, *, as_time: float | None = None, root_only: bool = False
    ) -> T:
        """
        另见 :meth:`~.Item.current`
        """
        if as_time is None:
            params = updater_params_ctx.get(None)
            if params is not None:
                as_time = params.global_t
        if as_time is None:
            as_time = Animation.global_t_ctx.get(None)

        if as_time is None:
            as_time = self.current_time

        root = self.compute_item(item, as_time, False)
        if not root_only:
            child_restorer = partial(self.item_current, as_time=as_time)
            root._unstore(child_restorer)
        return root

    # endregion

    # region ItemAppearance.visibility

    def is_visible(self, item: Item) -> bool:
        """
        判断特定的物件目前是否可见

        另见：:meth:`show`、:meth:`hide`
        """
        # 在运行 construct 过程中，params 是 None，返回值表示最后状态是否可见
        params = updater_params_ctx.get(None)
        if params is None:
            return len(self.item_appearances[item].visibility) % 2 == 1

        # 在 updater 的回调函数中，params 不是 None，返回值表示在这时是否可见
        return self.item_appearances[item].is_visible_at(params.global_t)

    def _show(self, item: Item) -> None:
        gaps = self.item_appearances[item].visibility
        if len(gaps) % 2 != 1:
            gaps.append(self.time_aligner.align_and_record(self.current_time))

    def show(self, *roots: Item, root_only=False) -> None:
        """
        显示物件
        """
        for root in roots:
            for item in root.walk_self_and_descendants(root_only):
                self._show(item)

    def _hide(self, item: Item) -> None:
        gaps = self.item_appearances[item].visibility
        if len(gaps) % 2 == 1:
            gaps.append(self.time_aligner.align_and_record(self.current_time))

    def hide(self, *roots: Item, root_only=False) -> None:
        """
        隐藏物件
        """
        for root in roots:
            for item in root.walk_self_and_descendants(root_only):
                self._hide(item)

    def hide_all(self) -> None:
        """
        隐藏显示中的所有物件
        """
        t = self.time_aligner.align_and_record(self.current_time)
        for appr in self.item_appearances.values():
            gaps = appr.visibility
            if len(gaps) % 2 == 1:
                gaps.append(t)

    def visible_items(self) -> list[Item]:
        return [
            item  #
            for item, appr in self.item_appearances.items()
            if len(appr.visibility) % 2 == 1
        ]

    # endregion

    def add_extra_render_group(
        self,
        t_range: TimeRange,
        func: RenderGroupFn,
        related_items: list[Item] | None,
    ) -> None:
        self.extra_render_groups.append(
            ExtraRenderGroup(t_range, func, related_items),
        )

    # region inspect lineno

    def _extract_lineno_in_construct(self) -> int | None:
        """
        得到当前在 :meth:`construct` 中执行到的行数
        """
        frame = inspect.currentframe()
        while frame is not None:
            f_back = frame.f_back

            if f_back is self._build_frame and frame.f_code.co_filename == inspect.getfile(
                self.__class__
            ):
                return frame.f_lineno

            frame = f_back

        return None

    def get_lineno_at_time(self, time: float):
        """
        根据 ``time`` 得到对应执行到的行数
        """
        toc = self.times_of_code
        if not toc:
            return -1

        idx = bisect(toc, time, key=lambda x: x.time)
        idx = clip(idx, 0, len(toc) - 1)
        return toc[idx].line

    # endregion


class ItemAppearance:
    """
    包含与物件显示有关的对象

    - ``self.stack`` 即 :class:`~.AnimStack` 对象

    - ``self.visiblility`` 是一个列表，存储物件显示/隐藏的时间点
        - 列表中偶数下标（0、2、...）的表示开始显示的时间点，奇数下标（1、3、...）的表示隐藏的时间点
        - 例如，如果列表中是 ``[3, 4, 8]``，则表示在第 3s 显示，第 4s 隐藏，并且在第 8s 后一直显示
        - 这种记录方式是 :meth:`TimelineBase.is_visible`、:meth:`TimelineBase.show`、:meth:`TimelineBase.hide` 运作的基础

    - ``self.renderer`` 表示所使用的渲染器对象
    """

    def __init__(self, item: Item, aligner: TimeAligner):
        self.stack = AnimStack(item, aligner)
        self.visibility: list[float] = []
        self.renderer: Renderer | None = None

    def is_visible_at(self, t: float) -> bool:
        """
        在 ``t`` 时刻，物件是否可见
        """
        idx = bisect(self.visibility, t)
        return idx % 2 == 1

    def render(self, data: Item) -> None:
        if self.renderer is None:
            self.renderer = data.create_renderer()
        self.renderer.render(data)


class ItemAppearances(defaultdict[Item, ItemAppearance]):
    """
    本质上是一个 ``{Item: ItemAppearance}`` 的 ``dict``

    但是如果 ``key`` 不存在，则会自动新建一个 ``key`` 物件
    所对应的 :class:`ItemAppearance`，并记录其当前状态作为初始状态
    """

    def __init__(self, time_aligner: TimeAligner):
        super().__init__()
        self.time_aligner = time_aligner

    def __missing__(self, key: Item) -> ItemAppearance:
        self[key] = value = ItemAppearance(key, self.time_aligner)
        return value
