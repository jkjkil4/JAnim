from __future__ import annotations

import inspect
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Iterable, Self

from tqdm import tqdm as ProgressDisplay

from janim.anims.anim_stack import AnimStack
from janim.anims.animation import FOREVER, Animation, ApplyAligner, ItemAnimation
from janim.anims.method_updater_meta import METHOD_UPDATER_KEY, MethodUpdaterInfo
from janim.anims_core.time import TimeRange
from janim.components.component import Component
from janim.constants import C_LABEL_ANIM_ABSTRACT
from janim.exception import UpdaterError
from janim.items.item import Item
from janim.locale import get_translator
from janim.render.base import Renderer
from janim.utils.rate_functions import RateFunc, linear
from janim.utils.simple_functions import clip

_ = get_translator('janim.anims.updater')


@dataclass
class UpdaterParams:
    """
    ``Updater`` 调用时会传递的参数，用于标注时间信息以及动画进度
    """

    global_t: float
    alpha: float
    range: TimeRange
    extra_data: Any | None

    _updater: _DataUpdater | GroupUpdater | None

    @property
    def elapsed(self) -> float:
        return self.global_t - self.range.at

    def __enter__(self) -> Self:
        self.token = updater_params_ctx.set(self)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        updater_params_ctx.reset(self.token)


@dataclass
class StepUpdaterParams:
    """
    :class:`StepUpdater` 调用时会传递的参数，用于标注时间信息以及动画进度
    """

    global_t: float
    dt: float
    range: TimeRange
    n: int

    _updater: _StepUpdater

    def __enter__(self) -> Self:
        self.token = updater_params_ctx.set(self)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        updater_params_ctx.reset(self.token)


updater_params_ctx: ContextVar[UpdaterParams | StepUpdaterParams] = ContextVar('updater_params_ctx')

type DataUpdaterFn[T] = Callable[[T, UpdaterParams], Any]
type GroupUpdaterFn[T] = Callable[[T, UpdaterParams], Any]
type ItemUpdaterFn = Callable[[UpdaterParams], Item]
type StepUpdaterFn[T] = Callable[[T, StepUpdaterParams], Any]


def _call_two_func(func1: Callable, func2: Callable, *args, **kwargs) -> None:
    func1(*args, **kwargs)
    func2(*args, **kwargs)


class DataUpdater[T: Item](Animation):
    """
    以时间为参数对物件的数据进行修改

    例如：

    .. code-block:: python

        class Example(Timeline):
            def construct(self) -> None:
                rect = Rect()
                rect.points.to_border(LEFT)

                self.play(
                    DataUpdater(
                        rect,
                        lambda data, p: data.points.rotate(p.alpha * 180 * DEGREES).shift(p.alpha * 6 * RIGHT)
                    )
                )

    会产生一个“矩形从左侧旋转着移动到右侧”的动画

    并且，可以对同一个物件作用多个 updater，各个 updater 会依次调用

    .. hint::

        默认 ``root_only=True`` 即只对根物件应用该 updater；需要设置 ``root_only=False`` 才会对所有后代物件也应用该 updater

    另见 :ref:`basic_examples` 中的 ``UpdaterExample``
    """

    label_color = C_LABEL_ANIM_ABSTRACT

    def __init__(
        self,
        item: T,
        func: DataUpdaterFn[T],
        *,
        extra: Callable[[Item], Any | None] = lambda x: None,
        lag_ratio: float = 0,
        show_at_begin: bool = True,
        hide_at_end: bool = False,
        become_at_end: bool = True,
        skip_null_items: bool = True,
        root_only: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.item = item
        self.func = func
        self.extra = extra
        self.lag_ratio = lag_ratio
        self.show_at_begin = show_at_begin
        self.hide_at_end = hide_at_end
        self.become_at_end = become_at_end
        self.skip_null_items = skip_null_items
        self.root_only = root_only

    def add_post_updater(self, func: DataUpdaterFn[T]) -> Self:
        orig_func = self.func
        self.func = lambda data, p: _call_two_func(orig_func, func, data, p)
        return self

    def _time_fixed(self) -> None:
        items: list[Item] = []
        for item in self.item.walk_self_and_descendants(self.root_only):
            if self.skip_null_items and item.is_null():
                # 这两行是为了 selector 中能够正确选择到物件
                self.timeline.track(item)
                self.schedule_show_and_hide(item, self.show_at_begin, self.hide_at_end)
            else:
                items.append(item)
        count = len(items)

        for i, item in enumerate(items):
            stack = self.timeline.item_appearances[item].stack

            sub_updater = _DataUpdater(
                self,
                item,
                self.func,
                self.extra(item),
                self.lag_ratio,
                i,
                count,
                show_at_begin=self.show_at_begin,
                hide_at_end=self.hide_at_end,
            )
            sub_updater.transfer_params(self)
            sub_updater.finalize()

            if self.become_at_end and self.t_range.end is not FOREVER:
                item.restore(stack.compute(self.t_range.end, True, get_at_left=True))
                stack.detect_change(item, self.t_range.end, force=True)


class _DataUpdater(ItemAnimation):
    def __init__(
        self,
        generate_by: DataUpdater,
        item: Item,
        func: DataUpdaterFn,
        extra_data: Any | None,
        lag_ratio: float,
        index: int,
        count: int,
        **kwargs,
    ):
        super().__init__(item, **kwargs)
        self._generate_by = generate_by
        self.func = func
        self.extra_data = extra_data
        self.lag_ratio = lag_ratio
        self.index = index
        self.count = count

    def apply(self, data: Item, p: ItemAnimation.ApplyParams) -> None:
        with UpdaterParams(
            p.global_t,
            self.get_sub_alpha(self.get_alpha_on_global_t(p.global_t)),
            self.t_range,
            self.extra_data,
            self,
        ) as params:
            self.func(data, params)

    def get_sub_alpha(self, alpha: float) -> float:
        """依据 ``lag_ratio`` 得到特定子物件的 ``sub_alpha``"""
        lag_ratio = self.lag_ratio
        full_length = (self.count - 1) * lag_ratio + 1
        value = alpha * full_length
        lower = self.index * lag_ratio
        return clip((value - lower), 0, 1)


class GroupUpdater[T: Item](Animation):
    """
    以时间为参数对一组物件的数据进行修改

    .. warning::

        该 Updater 假设 ``func`` 不会改变 ``item`` 后代物件结构，如果改变结构（例如增删子物件、:meth:`~.Item.become` 结构不一致等情况），则可能导致意外行为
    """

    label_color = C_LABEL_ANIM_ABSTRACT

    def __init__(
        self,
        item: T,
        func: GroupUpdaterFn[T],
        *,
        show_at_begin: bool = True,
        hide_at_end: bool = False,
        become_at_end: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.item = item
        self.func = func
        self.show_at_begin = show_at_begin
        self.hide_at_end = hide_at_end
        self.become_at_end = become_at_end

        self.applied: bool = False

    def add_post_updater(self, func: GroupUpdaterFn[T]) -> Self:
        orig_func = self.func
        self.func = lambda group, p: _call_two_func(orig_func, func, group, p)
        return self

    def _time_fixed(self) -> None:
        self.data = self.item.copy()

        sub_items = list(self.item.walk_self_and_descendants())
        stacks = [self.timeline.item_appearances[item].stack for item in sub_items]
        updaters = [
            _GroupUpdater(
                self,
                item,
                data,
                stacks,
                show_at_begin=self.show_at_begin,
                hide_at_end=self.hide_at_end,
            )
            for item, data in zip(sub_items, self.data.walk_self_and_descendants())
        ]

        if self.become_at_end and self.t_range.end is not FOREVER:
            for item, stack in zip(sub_items, stacks):
                item.restore(stack.compute(self.t_range.end, True, get_at_left=True))

            with UpdaterParams(self.t_range.end, 1, self.t_range, None, self) as params:
                self.func(self.item, params)

            for item, stack in zip(sub_items, stacks):
                stack.detect_change(item, self.t_range.end, force=True)

        for sub_updater in updaters:
            sub_updater.transfer_params(self)
            sub_updater.finalize()

    def apply_for_group(self, global_t: float) -> None:
        if self.applied:
            return

        with UpdaterParams(
            global_t,
            self.get_alpha_on_global_t(global_t),
            self.t_range,
            None,
            self,
        ) as params:
            self.func(self.data, params)

        self.applied = True


class _GroupUpdater(ApplyAligner):
    def __init__(
        self,
        generate_by: GroupUpdater,
        item: Item,
        data: Item,
        stacks: list[AnimStack],
        **kwargs,
    ):
        super().__init__(item, stacks, **kwargs)
        self._generate_by: GroupUpdater = generate_by
        self.data = data

    def pre_apply(self, data: Item, p: ItemAnimation.ApplyParams) -> None:
        self._generate_by.applied = False
        self.data.restore(data)

    def apply(self, data: Item, p: ItemAnimation.ApplyParams) -> None:
        self._generate_by.apply_for_group(p.global_t)
        data.restore(self.data)


class MethodUpdater(Animation):
    """
    依据物件的变换而创建的 updater

    具体参考 :meth:`~.Item.update`
    """

    label_color = (214, 185, 253)  # C_LABEL_ANIM_ABSTRACT 的变体

    class ActionType(Enum):
        GetAttr = 0
        Call = 1

    def __init__(
        self,
        item: Item,
        obj: Item | Item._AsTypeWrapper,
        show_at_begin: bool = True,
        hide_at_end: bool = False,
        become_at_end: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.item = item
        self.obj = obj
        self.show_at_begin = show_at_begin
        self.hide_at_end = hide_at_end
        self.become_at_end = become_at_end

        self.updaters: list[tuple[str | None, Callable, tuple, dict, bool | None]] = []
        self.grouply: bool = False

    class _FakeCmpt:
        def __init__(
            self,
            anim: MethodUpdater,
            cmpt_name: str,
            cmpt: Component,
            obj: Component | Item._AsTypeWrapper,
        ):
            self.anim = anim
            self.cmpt_name = cmpt_name
            self.cmpt = cmpt
            self.obj = obj

        def __getattr__(self, name: str):
            if name == 'r':
                return self.anim

            attr = getattr(self.obj, name, None)
            info: MethodUpdaterInfo | None = getattr(attr, METHOD_UPDATER_KEY, None)
            if info is None:
                raise UpdaterError(
                    _('There is no updatable method named {name} in {cmpt}').format(
                        name=name,
                        cmpt=self.cmpt.__class__.__name__,
                    )
                )

            def wrapper(*args, root_only: bool | None = None, **kwargs):
                if info.grouply:
                    self.anim.grouply = True
                self.anim.updaters.append((self.cmpt_name, info.updater, args, kwargs, root_only))
                return self

            return wrapper

        def __anim__(self) -> Animation:
            return self.anim

    def __getattr__(self, name: str):
        attr = getattr(self.obj, name, None)
        cmpt = self.get_real_component(attr)
        if cmpt is not None:
            return MethodUpdater._FakeCmpt(self, name, cmpt, attr)

        info: MethodUpdaterInfo | None = getattr(attr, METHOD_UPDATER_KEY, None)
        if info is None:
            raise UpdaterError(
                _('{item} has no component or updatable method named {name}').format(
                    item=self.item.__class__.__name__,
                    name=name,
                )
            )

        def wrapper(*args, root_only: bool | None = None, **kwargs):
            if info.grouply:
                self.grouply = True
            self.updaters.append((None, info.updater, args, kwargs, root_only))
            return self

        return wrapper

    @staticmethod
    def get_real_component(attr: Component | Item._AsTypeWrapper) -> Component | None:
        if isinstance(attr, Component):
            return attr
        if isinstance(attr, Item._AsTypeWrapper) and isinstance(attr._astype_obj, Component):
            return attr._astype_obj
        return None

    def updater(self, data: Item, p: UpdaterParams) -> None:
        for cmpt_name, updater, args, kwargs, root_only in self.updaters:
            obj = data if cmpt_name is None else data.components[cmpt_name]
            if root_only is None:
                updater(obj, p, *args, **kwargs)
            else:
                if self.grouply or p.extra_data:
                    updater(obj, p, *args, **kwargs, root_only=root_only)

    def _time_fixed(self) -> None:
        if not self.grouply:
            sub_updater = DataUpdater(
                self.item,
                self.updater,
                extra=lambda item: item is self.item,  # 仅根物件的为 True，用于辅助 root_only
                root_only=False,
                show_at_begin=self.show_at_begin,
                hide_at_end=self.hide_at_end,
                become_at_end=self.become_at_end,
            )
        else:
            sub_updater = GroupUpdater(
                self.item,
                self.updater,
                show_at_begin=self.show_at_begin,
                hide_at_end=self.hide_at_end,
                become_at_end=self.become_at_end,
            )

        sub_updater._generate_by = self
        sub_updater.transfer_params(self)
        sub_updater.finalize()


class MethodUpdaterArgsBuilder:
    """
    使得 ``.update`` 和 ``.update(...)`` 后可以进行同样的操作
    """

    def __init__(self, item: Item):
        self.item = item
        self.obj = item._astype_wrapper or item

    def __call__(self, **kwargs):
        return MethodUpdater(self.item, self.obj, **kwargs)

    def __getattr__(self, name):
        return getattr(MethodUpdater(self.item, self.obj), name)


class ItemUpdater(Animation):
    """
    以时间为参数显示物件

    也就是说，在 :class:`ItemUpdater` 执行时，对于每帧，都会执行 ``func``，并显示 ``func`` 返回的物件

    在默认情况下：

    - 传入的 ``item`` 会在动画的末尾被替换为动画最后一帧 ``func`` 所返回的物件，传入 ``become_at_end=False`` 以禁用
    - 传入的 ``item`` 会在动画开始时隐藏，在动画结束后显示，传入 ``hide_at_begin=False`` 和 ``show_at_end=False`` 以禁用
    - 若传入 ``item=None``，则以上两点都无效

    另见 :ref:`basic_examples` 中的 ``UpdaterExample``
    """

    label_color = C_LABEL_ANIM_ABSTRACT

    def __init__(
        self,
        item: Item | None,
        func: ItemUpdaterFn,
        *,
        hide_at_begin: bool = True,
        show_at_end: bool = True,
        become_at_end: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.func = func
        self.item = item
        self.hide_at_begin = hide_at_begin
        self.show_at_end = show_at_end
        self.become_at_end = become_at_end

        self.renderers: dict[type, Renderer] = {}

    def _time_fixed(self) -> None:
        self.timeline.add_extra_render_group(
            self.t_range,
            self.render_group_fn,
            None if self.item is None else [self.item],
        )

        if self.item is None:
            return

        # 因为如果需要在动画结束后替换物件，那么前后的后代物件可能会不同
        # 因此这里采用先记录后代物件的方式，再 schedule 对这些记录的物件的隐藏和显示
        # 而不是直接 schedule 物件的隐藏和显示
        hide_items = list(self.item.walk_self_and_descendants())
        show_items = hide_items

        # 在动画结束后，自动使用动画最后一帧的物件替换原有的
        if self.become_at_end and self.t_range.end is not FOREVER:
            with UpdaterParams(self.t_range.end, 1, self.t_range, None, self) as params:
                self.item.become(self.call(params), auto_visible=False)
                show_items = list(self.item.walk_self_and_descendants())
                for item in show_items:
                    stack = self.timeline.item_appearances[item].stack
                    stack.detect_change(item, self.t_range.end, force=True)

        # 在动画开始时自动隐藏，在动画结束时自动显示
        # 可以将 ``hide_on_begin`` 和 ``show_on_end`` 置为 ``False`` 以禁用
        if self.hide_at_begin:
            self.timeline.schedule(self.t_range.at, self.timeline.hide, *hide_items, root_only=True)
        if self.show_at_end and self.t_range.end is not FOREVER:
            self.timeline.schedule(
                self.t_range.end, self.timeline.show, *show_items, root_only=True
            )

    def call(self, p: UpdaterParams) -> Item:
        ret = self.func(p)
        if not isinstance(ret, Item):
            raise UpdaterError(
                _(
                    'The function passed to ItemUpdater must return an item, but got {ret} instead, '
                    'defined in {file}:{lineno}'
                ).format(
                    ret=ret,
                    file=inspect.getfile(self.func),
                    lineno=inspect.getsourcelines(self.func)[1],
                )
            )
        return ret

    def get_renderer(self, item: Item) -> Renderer:
        renderer = self.renderers.get(item.__class__, None)
        if renderer is None:
            renderer = self.renderers[item.__class__] = item.renderer_cls()
        return renderer

    def render_group_fn(self):
        global_t = Animation.global_t_ctx.get()
        alpha = self.get_alpha_on_global_t(global_t)
        with UpdaterParams(global_t, alpha, self.t_range, None, self) as params:
            ret = self.call(params)

        return [(item, self.get_renderer(item).render) for item in ret.walk_self_and_descendants()]


class StepUpdater[T: Item](Animation):
    """
    按步更新物件，每次间隔 ``step`` 秒调用 ``func`` 进行下一步更新
    """

    label_color = C_LABEL_ANIM_ABSTRACT

    def __init__(
        self,
        item: T,
        func: StepUpdaterFn[T],
        step: float = 0.02,  # 默认每秒 50 次
        *,
        persistent_cache_step: float = 1,  # 默认每秒一个持久缓存
        #
        show_at_begin: bool = True,
        hide_at_end: bool = False,
        become_at_end: bool = True,
        #
        rate_func: RateFunc = linear,
        skip_null_items: bool = True,
        root_only: bool = True,
        #
        progress_bar: bool = True,
        **kwargs,
    ):
        super().__init__(rate_func=rate_func, **kwargs)
        self.item = item
        self.func = func

        self.step = step
        self.persistent_cache_step = persistent_cache_step

        self.show_at_begin = show_at_begin
        self.hide_at_end = hide_at_end
        self.become_at_end = become_at_end

        self.skip_null_items = skip_null_items
        self.root_only = root_only

        self.progress_bar = progress_bar

    def add_post_updater(self, updater: StepUpdaterFn[T]) -> Self:
        orig_func = self.func
        self.func = lambda data, p: _call_two_func(orig_func, updater, data, p)
        return self

    def _time_fixed(self) -> None:
        for item in self.item.walk_self_and_descendants(self.root_only):
            if self.skip_null_items and item.is_null():
                # 这两行是为了 selector 中能够正确选择到物件
                self.timeline.track(item)
                self.schedule_show_and_hide(item, self.show_at_begin, self.hide_at_end)
                continue

            sub_updater = _StepUpdater(
                self,
                item,
                self.func,
                self.step,
                self.persistent_cache_step,
                self.become_at_end,
                self.progress_bar,
                show_at_begin=self.show_at_begin,
                hide_at_end=self.hide_at_end,
            )
            sub_updater.transfer_params(self)
            sub_updater.finalize()


class _StepUpdater(ItemAnimation):
    def __init__(
        self,
        generate_by: StepUpdater,
        item: Item,
        func: StepUpdaterFn,
        step: float,
        persistent_cache_step: float,
        become_at_end: bool,
        progress_bar: bool,
        *,
        show_at_begin: bool,
        hide_at_end: bool,
    ):
        super().__init__(item, show_at_begin=show_at_begin, hide_at_end=hide_at_end)
        self._generate_by = generate_by
        self._cover_previous_anims = True

        self.func = func
        self.step = step
        self.persistent_cache_step = persistent_cache_step
        self.become_at_end = become_at_end
        self.progress_bar = progress_bar

    def _time_fixed(self) -> None:
        self.first_data = self.timeline.compute_item(self.item, self.t_range.at, True).store()

        super()._time_fixed()

        self.data = self.first_data.store()

        chunk_size = max(1, round(self.persistent_cache_step / self.step))
        self._cache = ChunkedNearbyCache(
            chunk_size,
            self.first_data,
            lambda x: x.store(),
            progress_bar_desc=(
                f'StepUpdater({self.item.__class__.__name__})' if self.progress_bar else None
            ),
        )

        if self.become_at_end and self.t_range.end is not FOREVER:
            with self._cache.disable_temp_record():
                self.compute(self.item, self.t_range.end)

            apprs = self.timeline.item_appearances
            apprs[self.item].stack.detect_change(self.item, self.t_range.end)

    def apply(self, data: None, p: ItemAnimation.ApplyParams) -> Item:
        self.compute(self.data, p.global_t)
        return self.data

    def global_t_to_n(self, global_t: float) -> int:
        return max(0, int((global_t - self.t_range.at) // self.step))

    def n_to_global_t(self, n: int) -> float:
        return n * self.step + self.t_range.at

    def compute(self, data: Item, global_t: float) -> None:
        n = self.global_t_to_n(global_t)

        cache_n, cache = self._cache.get_nearest_cache(n)
        data.restore(cache)

        self._cache.scroll_tcache_to(n)

        for computing_n in self._cache.iterates(cache_n, n):
            with StepUpdaterParams(
                # 因为在这个函数中，经历了 global_t_to_n，再 n_to_global_t
                # 如果这个 updater 作用的物件有使用其它 StepUpdater 作用中的物件，会再次 global_t_to_n
                # 最后的这次 global_t_to_n 很有可能由于浮点数误差导致 n 意外小 1，导致一些错误的表现
                # 所以这里给它们加上了 1e-5
                self.n_to_global_t(computing_n) + 1e-5,
                self.step,
                self.t_range,
                computing_n,
                self,
            ) as params:
                self.func(data, params)

            self._cache.record(data, computing_n)


class ChunkedNearbyCache[T]:
    """
    用于辅助 :class:`StepUpdater` 的步进缓存类

    :param chunk_size: 每个 chunk 的元素数量

    技术细节：

    -   ``pcache`` 会存储每个 chunk 开头的元素

    -   ``tcache`` 的会存储当前活跃位置邻近的三个 chunk（当前以及前后各一个）

        每个 chunk 中存储除了 chunk 开头的元素外的剩下最多 ``chunk_size - 1`` 个元素
    """

    _disable_temp_record_ctx = ContextVar('_disable_temp_record_ctx', default=False)

    def __init__(
        self,
        chunk_size: int,
        first_data: T,
        get_copy_func: Callable[[T], T],
        *,
        progress_bar_desc: str | None,
    ):
        # persistent_cache abbr. pcache
        self._chunk_size = chunk_size
        self._pcache: list[T] = [first_data]
        # temporary_cache abbr. tcache
        self._tcache_at_chunk: int = 0  # 表示 tcache_chunks 中间那个 list 对应的全局 chunk 下标
        self._tcache_chunks: list[list[T]] = [[], [], []]

        self._get_copy_func = get_copy_func
        self._progress_bar_desc = progress_bar_desc

    def _tcache_idx_to_n(self, local_chunk_idx: int, elem_idx: int) -> int:
        # 注：tcache 跳过 pcache 中已记录的项
        # 所以 elem_idx 下标 0 对应整除 chunksize 为 1 的 n
        chunk_idx = self._tcache_at_chunk - 1 + local_chunk_idx
        return self._chunk_size * chunk_idx + (elem_idx + 1)

    def _n_to_tcache_idx(self, n: int) -> tuple[int, int]:
        # 注：若 n 能被 chunksize 整除，则 elem_idx 会返回 -1
        chunk_idx, mod = divmod(n, self._chunk_size)
        local_chunk_idx = chunk_idx - self._tcache_at_chunk + 1
        return (local_chunk_idx, mod - 1)

    @contextmanager
    def disable_temp_record(self):
        """
        通过 ``with`` 语句在其内部临时停止记录临时缓存

        用于 :class:`StepUpdater` 的 ``become_at_end`` 处理
        """
        token = self._disable_temp_record_ctx.set(True)
        try:
            yield
        finally:
            self._disable_temp_record_ctx.reset(token)

    def get_nearest_cache(self, n: int) -> tuple[int, T]:
        """
        得到 ``n`` 往前（包括 ``n`` ）的最近的一个缓存
        """
        local_chunk_idx, elem_idx = self._n_to_tcache_idx(n)
        if (
            elem_idx != -1
            and 0 <= local_chunk_idx < 3
            and (tcache_chunk := self._tcache_chunks[local_chunk_idx])
        ):
            found_idx = min(len(tcache_chunk) - 1, elem_idx)
            found_n = self._tcache_idx_to_n(local_chunk_idx, found_idx)
            return (found_n, tcache_chunk[found_idx])
        else:
            chunk_idx = min(len(self._pcache) - 1, n // self._chunk_size)
            found_n = chunk_idx * self._chunk_size
            return (found_n, self._pcache[chunk_idx])

    def scroll_tcache_to(self, n: int) -> None:
        """
        滚动裁剪 ``tcache_chunks``，使得 ``tcache_at_chunk`` 和 ``n`` 对应的 chunk 对上
        """
        chunk_idx = n // self._chunk_size
        offset = clip(chunk_idx - self._tcache_at_chunk, -3, 3)
        if offset > 0:
            left = self._tcache_chunks[offset:]
            self._tcache_chunks = [
                *left,
                *([] for _ in range(offset)),
            ]
        elif offset < 0:
            right = self._tcache_chunks[: 3 + offset]
            self._tcache_chunks = [
                *([] for _ in range(-offset)),
                *right,
            ]
        self._tcache_at_chunk = chunk_idx

        assert len(self._tcache_chunks) == 3

    def iterates(self, cache_n: int, n: int) -> Iterable[int]:
        """
        即 ``range(cache_n + 1, n + 1)``

        如果两者之差过大，则会套入 ``ProgressDisplay`` （即 ``tqdm`` ） 以显示进度条
        """
        rg = range(cache_n + 1, n + 1)
        if self._progress_bar_desc is not None and len(rg) > 2 * self._chunk_size:
            rg = ProgressDisplay(
                rg,
                desc=self._progress_bar_desc,
                leave=False,
                dynamic_ncols=True,
            )
        return rg

    def record(self, data: T, n: int) -> None:
        """
        将缓存记入 ``pcache`` 或 ``tcache`` 中
        """
        # 检查是否可记入 pcache
        chunk_idx, mod = divmod(n, self._chunk_size)
        if mod == 0 and chunk_idx == len(self._pcache):
            self._pcache.append(self._get_copy_func(data))

        # 检查是否可记入 tcache
        if not self._disable_temp_record_ctx.get():
            local_chunk_idx, elem_idx = self._n_to_tcache_idx(n)
            if elem_idx != -1 and 0 <= local_chunk_idx < 3:
                tcache_chunk = self._tcache_chunks[local_chunk_idx]
                if elem_idx == len(tcache_chunk):
                    tcache_chunk.append(self._get_copy_func(data))
