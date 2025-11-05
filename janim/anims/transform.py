
import itertools as it
import types
from collections import defaultdict
from enum import Enum
from functools import partial
from typing import Callable, Generator, Iterable

from janim.anims.animation import Animation, ItemAnimation
from janim.anims.composition import AnimGroup
from janim.anims.fading import FadeInFromPoint, FadeOutToPoint
from janim.constants import C_LABEL_ANIM_STAY, OUT
from janim.items.item import Item
from janim.items.points import Points
from janim.items.vitem import VItem
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.typing import Vect
from janim.utils.data import AlignedData
from janim.utils.iterables import resize_preserving_order
from janim.utils.paths import PathFunc, get_path_func

_ = get_local_strings('transform')


class Transform(Animation):
    '''
    创建从 ``src_item`` 至 ``target_item`` 的插值动画

    - ``path_arc`` 和 ``path_arc_axis`` 可以指定插值的圆弧路径的角度，若不传入则是直线
    - 也可以直接传入 ``path_func`` 来指定路径方法
    - 在默认情况（``flatten=False``）下需要保证两个物件的子物件结构能够对齐，否则会报错；可以传入 ``flatten=True`` 来忽略子物件结构
    - ``root_only`` 可以指定只对两个物件的根物件进行插值，而不对子物件进行插值
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

        flatten: bool = False,
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

        self.flatten = flatten
        self.root_only = root_only

        apprs = self.timeline.item_appearances

        for item in self.src_item.walk_self_and_descendants(root_only):
            apprs[item].stack.detect_change_if_not(item)
        if self.target_item is not self.src_item:
            for item in self.target_item.walk_self_and_descendants(root_only):
                apprs[item].stack.detect_change_if_not(item)

    def _time_fixed(self) -> None:
        self.align_data()

        self.additional_calls = [
            (aligned.union, partial(self.render, aligned, aligned.union.renderer_cls().render))
            for aligned in self.aligned.values()
        ]
        self.timeline.add_additional_render_calls_callback(
            self.t_range,
            lambda: self.additional_calls
        )

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

        if not self.flatten:
            align(self.src_item, self.target_item, not self.root_only)
        else:
            src_items = [
                item
                for item in self.src_item.walk_self_and_descendants(self.root_only)
                if not item.is_null()
            ]
            target_items = [
                item
                for item in self.target_item.walk_self_and_descendants(self.root_only)
                if not item.is_null()
            ]

            max_len = max(len(src_items), len(target_items))
            src_items = resize_preserving_order(src_items, max_len)
            target_items = resize_preserving_order(target_items, max_len)

            for item1, item2 in zip(src_items, target_items):
                align(item1, item2, False)

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


class MoveToTarget(Transform):
    '''
    详见 :meth:`~.Item.generate_target`
    '''

    def __init__(self, item: Item, **kwargs):
        super().__init__(
            item,
            item.target,
            **kwargs,
            hide_src=True,
            show_target=False,
            root_only=False
        )

    def _time_fixed(self):
        super()._time_fixed()

        def at_end():
            self.src_item.become(self.src_item.target, auto_visible=False)    # 因为下一句就是 show，所以传入了 auto_visible=False
            self.src_item.show()

        self.timeline.schedule(self.t_range.end, at_end)


class TransformInSegments(AnimGroup):
    '''
    依照切片列表进行 ``src`` 与 ``target`` 之间的变换
    '''

    label_color = C_LABEL_ANIM_STAY

    def __init__(
        self,
        src: Item,
        src_segments: Iterable[Iterable[int]] | Iterable[int],
        target: Item,
        target_segments: Iterable[Iterable[int]] | Iterable[int] | types.EllipsisType,
        *,
        trs_kwargs: dict = {},
        **kwargs
    ):
        anims = [
            Transform(src[l1:r1], target[l2:r2], **trs_kwargs)
            for (l1, r1), (l2, r2) in self.parse_segments(src_segments, target_segments)
        ]
        super().__init__(*anims, **kwargs)

    @staticmethod
    def parse_segments(src_segs, target_segs):
        if target_segs is ...:
            target_segs = src_segs
        return zip(
            TransformInSegments.parse_segment(src_segs),
            TransformInSegments.parse_segment(target_segs),
            strict=True
        )

    @staticmethod
    def parse_segment(segs: Iterable[Iterable[int]] | Iterable[int]) -> Generator[tuple[int, int], None, None]:
        '''
        ``[[a, b, c], [d, e]]`` -> ``[[a, b], [b, c], [d, e]]``
        '''
        assert len(segs) > 0
        if not isinstance(segs[0], Iterable):
            segs = [segs]

        for seg in segs:
            for a, b in it.pairwise(seg):
                yield (min(a, b), max(a, b))


class MethodTransform(Transform):
    '''
    依据物件的变换而创建的补间过程

    具体参考 :meth:`~.Item.anim`
    '''
    label_color = (255, 189, 129)    # C_LABEL_ANIM_STAY 的变体

    class ActionType(Enum):
        GetAttr = 0
        Call = 1

    def __init__(
        self,
        item: Item,
        show_at_begin: bool = True,
        hide_at_end: bool = False,
        **kwargs
    ):
        super().__init__(item, item, **kwargs)
        self.show_at_begin = show_at_begin
        self.hide_at_end = hide_at_end
        self.delayed_actions: list[tuple[MethodTransform.ActionType, str | tuple[tuple, dict]]] = []

    def __getattr__(self, name: str):
        self.delayed_actions.append((MethodTransform.ActionType.GetAttr, name))
        return self

    def __call__(self, *args, **kwargs):
        self.delayed_actions.append((MethodTransform.ActionType.Call, (args, kwargs)))
        return self

    def _time_fixed(self) -> None:
        obj = self.src_item
        for type, value in self.delayed_actions:
            if type is MethodTransform.ActionType.GetAttr:
                obj = getattr(obj, value)
            else:   # Call
                args, kwargs = value
                obj = obj(*args, **kwargs)

        apprs = self.timeline.item_appearances

        for item in self.src_item.walk_self_and_descendants():
            apprs[item].stack.detect_change(item, self.t_range.end)

        self.align_data()

        for item in self.src_item.walk_self_and_descendants():
            aligned = self.aligned[(item, item)]

            sub_updater = _MethodTransform(self,
                                           item,
                                           self.path_func,
                                           aligned,
                                           show_at_begin=self.show_at_begin,
                                           hide_at_end=self.hide_at_end)
            sub_updater.transfer_params(self)
            sub_updater.finalize()


class MethodTransformArgsBuilder:
    '''
    使得 ``.anim`` 和 ``.anim(...)`` 后可以进行同样的操作
    '''
    def __init__(self, item: Item):
        self.item = item

    def __call__(self, **kwargs):
        return MethodTransform(self.item, **kwargs)

    def __getattr__(self, name):
        return getattr(MethodTransform(self.item), name)


class _MethodTransform(ItemAnimation):
    def __init__(
        self,
        generate_by: MethodTransform,
        item: Item,
        path_func: PathFunc,
        aligned: AlignedData[Item],
        **kwargs
    ):
        super().__init__(item, **kwargs)
        self._generate_by = generate_by
        self._cover_previous_anims = True
        self.path_func = path_func
        self.aligned = aligned

    def apply(self, data: None, p: ItemAnimation.ApplyParams) -> Item:
        self.aligned.union.interpolate(
            self.aligned.data1,
            self.aligned.data2,
            self.get_alpha_on_global_t(p.global_t),
            path_func=self.path_func
        )
        return self.aligned.union


class FadeTransform(AnimGroup):
    label_color = C_LABEL_ANIM_STAY

    def __init__(
        self,
        src: Item,
        target: Item,
        *,
        hide_src: bool = True,
        show_target: bool = True,

        path_arc: float = 0,
        path_arc_axis: Vect = OUT,
        path_func: PathFunc | None = None,

        src_root_only: bool = False,
        target_root_only: bool = False,

        collapse: bool = True,
        **kwargs
    ):
        src_copy = src.copy(root_only=src_root_only)
        src_copy.set(alpha=0)
        src_copy(Points) \
            .points.replace(target, stretch=True, root_only=src_root_only, item_root_only=target_root_only)

        target_copy = target.copy(root_only=target_root_only)
        target_copy.set(alpha=0)
        target_copy(Points) \
            .points.replace(src, stretch=True, root_only=target_root_only, item_root_only=src_root_only)

        super().__init__(
            Transform(
                src, src_copy,
                hide_src=hide_src,
                show_target=False,
                path_arc=path_arc,
                path_arc_axis=path_arc_axis,
                path_func=path_func,
                root_only=src_root_only
            ),
            Transform(
                target_copy, target,
                hide_src=False,
                show_target=show_target,
                path_arc=path_arc,
                path_arc_axis=path_arc_axis,
                path_func=path_func,
                root_only=target_root_only
            ),
            collapse=collapse,
            **kwargs
        )


class TransformMatchingShapes(AnimGroup):
    '''
    匹配形状进行变换

    - ``mismatch`` 表示对于不匹配的形状的处理
    - 注：所有传入该动画类的额外参数都会被传入 ``mismatch`` 的方法中
    '''

    label_color = C_LABEL_ANIM_STAY

    def __init__(
        self,
        src: Item,
        target: Item,
        *,
        mismatch: tuple[Callable, Callable] = (FadeOutToPoint, FadeInFromPoint),
        duration: float = 2,
        lag_ratio: float = 0,
        collapse: bool = True,
        **kwargs
    ):
        src_mismatch_method, target_mismatch_method = mismatch

        def self_and_descendant_with_points(item: Item) -> list[VItem]:
            return [
                item
                for item in item.walk_self_and_descendants()
                if isinstance(item, VItem) and item.points.has()
            ]

        src_pieces = self_and_descendant_with_points(src)
        target_pieces = self_and_descendant_with_points(target)

        src_matched: list[VItem] = []
        target_matched: list[VItem] = []

        for piece1, piece2 in it.product(src_pieces, target_pieces):
            if not piece1.points.same_shape(piece2):
                continue
            if piece1 in src_matched or piece2 in target_matched:
                continue
            src_matched.append(piece1)
            target_matched.append(piece2)

        src_mismatched = [
            piece
            for piece in src_pieces
            if piece not in src_matched
        ]
        target_mismatched = [
            piece
            for piece in target_pieces
            if piece not in target_matched
        ]

        src_center = src(Points).points.box.center
        target_center = target(Points).points.box.center

        super().__init__(
            *[
                Transform(piece1, piece2, **kwargs)
                for piece1, piece2 in zip(src_matched, target_matched)
            ],
            *[
                src_mismatch_method(piece, target_center, **kwargs)
                for piece in src_mismatched
            ],
            *[
                target_mismatch_method(piece, src_center, **kwargs)
                for piece in target_mismatched
            ],
            duration=duration,
            lag_ratio=lag_ratio,
            collapse=collapse
        )
