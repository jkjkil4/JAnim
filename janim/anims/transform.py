from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Self

from janim.anims.animation import Animation, RenderCall
from janim.components.component import Component
from janim.constants import OUT
from janim.items.item import Item
from janim.typing import Vect
from janim.utils.data import AlignedData
from janim.utils.paths import PathFunc, path_along_arc, straight_path

if TYPE_CHECKING:
    from janim.anims.timeline import DynamicData


class Transform(Animation):
    label_color = (192, 156, 57)

    def __init__(
        self,
        src_item: Item,
        target_item: Item,
        *,
        path_arc: float = 0,
        path_arc_axis: Vect = OUT,
        path_func: PathFunc = None,

        hide_src: bool = True,
        show_target: bool = True,

        root_only: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.src_item = src_item
        self.target_item = target_item

        self.path_arc = path_arc
        self.path_arc_axis = path_arc_axis
        self.path_func = path_func

        self.hide_src = hide_src
        self.show_target = show_target

        self.root_only = root_only

        self.init_path_func()

    def init_path_func(self) -> None:
        if self.path_func is not None:
            return

        if self.path_arc == 0:
            self.path_func = straight_path
        else:
            self.path_func = path_along_arc(
                self.path_arc,
                self.path_arc_axis
            )

    def anim_init(self) -> None:
        '''
        进行物件数据的对齐
        '''
        self.aligned: dict[tuple[Item, Item], AlignedData[Item.Data[Item]]] = {}
        begin_times: defaultdict[Item, int] = defaultdict(int)
        end_times: defaultdict[Item, int] = defaultdict(int)

        def align(item1: Item, item2: Item, recurse: bool) -> None:
            tpl = (item1, item2)
            if tpl in self.aligned:
                return

            data1 = self.timeline.get_stored_data_at_right(item1, self.global_range.at, skip_dynamic_data=True)
            data2 = self.timeline.get_stored_data_at_left(item2, self.global_range.end, skip_dynamic_data=True)
            aligned = self.aligned[tpl] = data1.align_for_interpolate(data1, data2)
            begin_times[item1] += 1
            end_times[item2] += 1

            if recurse:
                for child1, child2 in zip(aligned.data1.children, aligned.data2.children):
                    align(child1, child2, True)

        align(self.src_item, self.target_item, not self.root_only)

        for (begin, end), aligned in self.aligned.items():
            times = begin_times.get(begin, 0)
            if times >= 2:
                aligned.data1.apart_alpha(times)

            times = end_times.get(end, 0)
            if times >= 2:
                aligned.data2.apart_alpha(times)

        self.set_render_call_list([
            RenderCall(
                aligned.data1.cmpt.depth,
                aligned.union.render
            )
            for aligned in self.aligned.values()
        ])

        if self.hide_src:
            self.timeline.schedule(self.global_range.at, self.src_item.hide, root_only=self.root_only)
        if self.show_target:
            self.timeline.schedule(self.global_range.end, self.target_item.show, root_only=self.root_only)

    def anim_on_alpha(self, alpha: float) -> None:
        '''
        对物件数据进行过渡插值
        '''
        for aligned in self.aligned.values():
            aligned.union.interpolate(aligned.data1, aligned.data2, alpha, path_func=self.path_func)


class MethodTransform[T: 'Item'](Transform):
    '''
    对物件进行变换并创建的补间过程

    例如：

    .. code-block:: python

        self.play(
            item.anim.points.scale(2)).r.color.set('green'))
        )

    该例子会创建将 ``item`` 缩放 2 倍并且设置为绿色的补间动画
    '''
    label_color = (165, 103, 44)

    def __init__(self, item: T, **kwargs):
        super().__init__(item, item, **kwargs)
        self.current_alpha = None

        self.timeline.detect_changes(item.walk_self_and_descendants())

    def do(self, func: Callable[[T], Any]) -> Self:
        func(self.src_item)
        return self

    def wrap_data(self, item: Item) -> DynamicData:
        def wrapper(global_t: float) -> Item.Data:
            alpha = self.get_alpha_on_global_t(global_t)
            aligned = self.aligned[(item, item)]

            union_copy = aligned.union._copy(aligned.union)
            union_copy.interpolate(aligned.data1, aligned.data2, alpha, path_func=self.path_func)

            return union_copy

        return wrapper

    def anim_pre_init(self) -> None:
        from janim.anims.timeline import ANIM_END_DELTA

        self.timeline.register_dynamic_data(self.src_item, self.wrap_data(self.src_item), self.global_range.at)
        if not self.root_only:
            for item in self.src_item.descendants():
                if (item, item) not in self.aligned:
                    continue

                self.timeline.register_dynamic_data(item, self.wrap_data(item), self.global_range.at)

        self.timeline.detect_changes(self.src_item.walk_self_and_descendants(),
                                     as_time=self.global_range.end - ANIM_END_DELTA)

    def anim_on_alpha(self, alpha: float) -> None:
        if alpha == self.current_alpha:
            return
        self.current_alpha = alpha
        super().anim_on_alpha(alpha)

    class _FakeCmpt:
        def __init__(self, anim: MethodTransform, cmpt: Component) -> None:
            self.anim = anim
            self.cmpt = cmpt

        def __getattr__(self, name: str):
            if name == 'r':
                return self.anim

            attr = getattr(self.cmpt, name, None)
            if attr is None or not callable(attr):
                raise KeyError(f'{self.cmpt.__class__.__name__} 中没有叫作 {name} 的可调用方法')

            def wrapper(*args, **kwargs):
                attr(*args, **kwargs)
                return self

            return wrapper

    def __getattr__(self, name: str):
        cmpt = self.src_item.components.get(name, None)
        if cmpt is not None:
            return MethodTransform._FakeCmpt(self, cmpt)

        attr = getattr(self.src_item, name, None)
        if attr is not None and callable(attr):
            def wrapper(*args, **kwargs):
                attr(*args, **kwargs)
                return self
            return wrapper

        raise KeyError(f'{self.src_item.__class__.__name__} 没有叫作 {name} 的组件或者可调用的方法')


class MethodTransformArgsBuilder:
    def __init__(self, item: Item):
        self.item = item

    def __call__(self, **kwargs):
        return MethodTransform(self.item, **kwargs)

    def __getattr__(self, name):
        return getattr(MethodTransform(self.item), name)
