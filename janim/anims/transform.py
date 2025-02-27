
from collections import defaultdict
from functools import partial
from typing import Callable

from janim.anims.animation import Animation
from janim.anims.timeline import Timeline
from janim.constants import C_LABEL_ANIM_STAY, OUT
from janim.items.item import Item
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.typing import Vect
from janim.utils.data import AlignedData
from janim.utils.paths import PathFunc, get_path_func

_ = get_local_strings('transform')


class Transform(Animation):
    '''
    创建从 ``src_item`` 至 ``target_item`` 的插值动画

    - ``path_arc`` 和 ``path_arc_axis`` 可以指定插值的圆弧路径的角度，若不传入则是直线
    - 也可以直接传入 ``path_func`` 来指定路径方法
    '''
    label_color = C_LABEL_ANIM_STAY

    def __init__(
        self,
        src_item: Item,
        target_item: Item,
        *,
        path_arc: float = 0,
        path_arc_axis: Vect = OUT,
        path_func: PathFunc | None = None,

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
        self.path_func = get_path_func(path_arc, path_arc_axis, path_func)

        self.hide_src = hide_src
        self.show_target = show_target

        self.root_only = root_only

        self.timeline = Timeline.get_context()
        apprs = self.timeline.item_appearances

        for item in self.src_item.walk_self_and_descendants(root_only):
            apprs[item].stack.detect_change_if_not(item)
        if self.target_item is not self.src_item:
            for item in self.target_item.walk_self_and_descendants(root_only):
                apprs[item].stack.detect_change_if_not(item)

    def _time_fixed(self) -> None:
        self.align_data()

        rc = Timeline.AdditionalRenderCalls(
            self.t_range,
            [
                (aligned.union, partial(self.render, aligned, aligned.union.renderer_cls().render))
                for aligned in self.aligned.values()
            ]
        )
        self.timeline.add_additional_render_calls(rc)

        # 在动画开始时自动隐藏源对象，在动画结束时自动显示目标对象
        # 可以将 ``hide_src`` 和 ``show_target`` 置为 ``False`` 以禁用
        if self.hide_src:
            self.timeline.schedule(self.t_range.at, self.src_item.hide, root_only=self.root_only)
        if self.show_target:
            self.timeline.schedule(self.t_range.end, self.target_item.show, root_only=self.root_only)

    def align_data(self) -> None:
        apprs = self.timeline.item_appearances

        self.aligned: dict[tuple[Item, Item], AlignedData[Item]] = {}
        begin_times: defaultdict[Item, int] = defaultdict(int)
        end_times: defaultdict[Item, int] = defaultdict(int)

        # 对齐物件
        def align(item1: Item, item2: Item, recurse: bool) -> None:
            tup = (item1, item2)
            if tup in self.aligned:
                return

            data1 = apprs[item1].stack.compute(self.t_range.at, True)
            data2 = apprs[item2].stack.compute(self.t_range.end, True)
            aligned = self.aligned[tup] = data1.align_for_interpolate(data1, data2)
            begin_times[item1] += 1
            end_times[item2] += 1

            if recurse:
                if bool(data1.get_children()) != bool(data2.get_children()):
                    spec1 = f'<"{item1.__class__.__name__}" {id(item1):X}>'
                    spec2 = f'<"{item2.__class__.__name__}" {id(item2):X}>'
                    log.warning(
                        _('The child items of {spec1} and {spec2} cannot be aligned '
                          'because their child items must either both be empty or both exist. '
                          'However, their child item counts are {len1} and {len2}, respectively.')
                        .format(spec1=spec1,
                                spec2=spec2,
                                len1=len(data1.get_children()),
                                len2=len(data2.get_children()))
                    )
                else:
                    for child1, child2 in zip(aligned.data1.stored_children, aligned.data2.stored_children):
                        align(child1, child2, True)

        align(self.src_item, self.target_item, not self.root_only)

        # 因为对齐后，可能会有多个一样的物件重叠在一起
        # 所以这里需要拆分这些物件的透明度，使得重叠在一起的相同物件在颜色混合后仍表现为原有的样子
        # 这样在动画进行时和进行前后之间就不会有突兀的切换
        for (begin, end), aligned in self.aligned.items():
            times = begin_times.get(begin, 0)
            if times >= 2:
                aligned.data1.apart_alpha(times)

            times = end_times.get(end, 0)
            if times >= 2:
                aligned.data2.apart_alpha(times)

    def render(self, aligned: AlignedData, func: Callable[[Item], None], data: Item) -> None:
        global_t = Animation.global_t_ctx.get()
        alpha = self.get_alpha_on_global_t(global_t)
        data.interpolate(aligned.data1, aligned.data2, alpha, path_func=self.path_func)
        func(data)
