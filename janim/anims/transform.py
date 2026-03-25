from __future__ import annotations

import difflib
import itertools as it
import types
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from functools import partial
from typing import Callable, Generator, Iterable

import numpy as np

from janim.anims.animation import Animation, ItemAnimation, TimeRange
from janim.anims.composition import AnimGroup
from janim.anims.fading import FadeIn, FadeInFromPoint, FadeOut, FadeOutToPoint
from janim.components.points import Cmpt_Points
from janim.constants import C_LABEL_ANIM_STAY, OUT
from janim.exception import TargetNotFoundError
from janim.items.item import Item
from janim.items.points import Points
from janim.items.text import Text, TextChar, TextLine
from janim.items.vitem import VItem
from janim.locale import get_translator
from janim.logger import log
from janim.typing import Vect
from janim.utils.data import AlignedData
from janim.utils.iterables import resize_preserving_order
from janim.utils.paths import PathFunc, get_path_func

_ = get_translator('janim.anims.transform')


class Transform(Animation):
    """
    创建从 ``src_item`` 到 ``target_item`` 的插值动画

    作用机制：在开始时隐藏源物件，在动画过程中播放“插值效果”，在结束后显示目标物件

    :param src_item: 变换的起始物件
    :param target_item: 变换的目标物件

    **路径与插值**

    :param path_arc: 插值路径的圆弧角度；为 ``0`` 时按直线插值
    :param path_arc_axis: 当使用圆弧路径时的旋转轴。
    :param path_func: 自定义路径函数；传入后会覆盖 ``path_arc`` 与 ``path_arc_axis`` 的默认路径行为

    **对齐策略**

    :param flatten: 是否忽略子物件层级并直接按顺序展平对齐；默认 ``False``，要求源与目标子结构可对齐
    :param root_only: 是否仅对根物件进行插值而不递归子物件

    **显隐与淡入淡出**

    :param hide_src: 动画开始时是否自动隐藏源物件
    :param show_target: 动画结束时是否自动显示目标物件
    :param src_fade: 仅当 ``hide_src=False`` 时生效；表示源物件在动画开头淡入的时长比例
    :param target_fade: 仅当 ``show_target=True`` 时生效；表示目标物件在动画末尾淡出的时长比例

    ``src_fade`` 与 ``target_fade`` 对半透明物件较为实用，可规避开始/结束时重叠导致的透明度突变

    ----

    基本示例：

    .. janim-example:: TransformExample
        :extract-from-test:
        :media: _static/videos/TransformExample.mp4
        :url: https://janim.readthedocs.io/zh-cn/latest/janim/anims/transform.html#transformexample

    对 ``hide_src`` 和 ``show_target`` 参数的演示：

    .. janim-example:: TransformHideShowExample
        :extract-from-test:
        :media: _static/videos/TransformHideShowExample.mp4
        :url: https://janim.readthedocs.io/zh-cn/latest/janim/anims/transform.html#transformhideshowexample

    对 ``src_fade`` 和 ``target_fade`` 参数的演示：

    .. janim-example:: TransformFadeExample
        :extract-from-test:
        :media: _static/videos/TransformFadeExample.mp4
        :url: https://janim.readthedocs.io/zh-cn/latest/janim/anims/transform.html#transformfadeexample
    """
    label_color = C_LABEL_ANIM_STAY

    def __init__(
        self,
        src_item: Item,
        target_item: Item,
        *,
        path_arc: float = 0,
        path_arc_axis: Vect = OUT,
        path_func: PathFunc | None = None,

        flatten: bool = False,
        root_only: bool = False,

        hide_src: bool = True,
        show_target: bool = True,

        src_fade: float = 0,
        target_fade: float = 0,
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

        self.src_fade = src_fade
        self.target_fade = target_fade

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
            lambda: self.additional_calls,
            [self.src_item, self.target_item]
        )

        # 在动画开始时自动隐藏源对象，在动画结束时自动显示目标对象
        # 可以将 ``hide_src`` 和 ``show_target`` 置为 ``False`` 以禁用
        if self.hide_src:
            self.timeline.schedule(self.t_range.at, self.src_item.hide, root_only=self.root_only)

        if self.show_target:
            self.timeline.schedule(self.t_range.end, self.target_item.show, root_only=self.root_only)

        # 对 src_fade 和 target_fade 的处理
        if not self.hide_src and self.src_fade != 0:
            fade_duration = self.t_range.duration * self.src_fade
            anim = FadeIn(self.src_item)
            anim.transfer_params(self)
            anim.t_range = TimeRange(self.t_range.at, self.t_range.at + fade_duration)
            anim.finalize()

        if self.show_target and self.target_fade != 0:
            fade_start = self.t_range.duration * (1 - self.target_fade)
            anim = FadeOut(self.target_item, hide_at_end=False)
            anim.transfer_params(self)
            anim.t_range = TimeRange(self.t_range.at + fade_start, self.t_range.end)
            anim.finalize()

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
                    for child1, child2 in zip(aligned.data1._stored_children, aligned.data2._stored_children):
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
    """
    详见 :meth:`~.Item.generate_target`

    .. janim-example:: MoveToTargetExample
        :extract-from-test:
        :media: _static/videos/MoveToTargetExample.mp4
        :url: https://janim.readthedocs.io/zh-cn/latest/janim/anims/transform.html#movetotargetexample
    """

    def __init__(self, item: Item, **kwargs):
        if item.target is None:
            raise TargetNotFoundError(
                _('You must use `.generate_target` to generate the target item '
                  'before using `MoveToTarget` to create animation')
            )
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
            self.src_item.become(self.src_item.target, auto_visible=False)    # 因为马上就是 show，所以传入了 auto_visible=False
            self.timeline.detect_changes(self.src_item.walk_self_and_descendants())
            self.src_item.show()

        self.timeline.schedule(self.t_range.end, at_end)


class TransformInSegments(AnimGroup):
    """
    依照切片列表进行 ``src`` 与 ``target`` 之间的变换

    ----

    **基本用法**

    .. code-block:: python

        TransformInSegments(a, [[0,3], [5,7]],
                            b, [[1,3], [5,7]])

    相当于

    .. code-block:: python

        AnimGroup(Transform(a[0:3], b[1:3]),
                  Transform(a[5:7], b[5:7]))

    **省略变换目标的切片**

    使用 ``...`` 表示与变换来源的切片相同

    .. code-block:: python

        TransformInSegments(a, [[0,3], [5,7]],
                            b, ...)

    相当于

    .. code-block:: python

        TransformInSegments(a, [[0,3], [5,7]],
                            b, [[0,3], [5,7]])

    **连续切片**

    .. code-block:: python

        TransformInSegments(a, [[0,3], [5,7,9]],
                            b, [[1,3], [4,7], [10,14]])

    相当于

    .. code-block:: python

        TransformInSegments(a, [[0,3], [5,7], [7,9]],
                            b, [[1,3], [4,7], [10,14]])

    **切片简写**

    如果总共只有一个切片，可以省略一层嵌套

    .. code-block:: python

        TransformInSegments(a, [0, 4, 6, 8],
                            b, ...)

    相当于

    .. code-block:: python

        TransformInSegments(a, [[0, 4, 6, 8]],
                            b, ...)

    **连续切片倒序**

    倒过来写即可使切片倒序

    .. code-block:: python

        TransformInSegments(a, [8, 6, 4, 0],
                            b, ...)

    相当于

    .. code-block:: python

        TransformInSegments(a, [[6,8], [4,6], [0,4]],
                            b, ...)

    请留意 Python 切片中左闭右开的原则，对于倒序序列 ``[8, 6, 4, 0]`` 来说则是左开右闭

    .. janim-example:: TransformInSegmentsExample
        :extract-from-test:
        :media: _static/videos/TransformInSegmentsExample.mp4
        :url: https://janim.readthedocs.io/zh-cn/latest/janim/anims/transform.html#transforminsegmentsexample
    """

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
        # ``[[a, b, c], [d, e]]`` -> ``[[a, b], [b, c], [d, e]]``
        assert len(segs) > 0
        if not isinstance(segs[0], Iterable):
            segs = [segs]

        for seg in segs:
            for a, b in it.pairwise(seg):
                yield (min(a, b), max(a, b))


class MethodTransform(Transform):
    """
    依据物件的变换而创建的补间过程

    具体参考 :meth:`~.Item.anim`

    .. janim-example:: MethodTransformExample
        :extract-from-test:
        :media: _static/videos/MethodTransformExample.mp4
        :url: https://janim.readthedocs.io/zh-cn/latest/janim/anims/transform.html#methodtransformexample
    """
    label_color = (255, 189, 129)    # C_LABEL_ANIM_STAY 的变体

    class _ActionType(Enum):
        GetAttr = 0
        Call = 1

    def __init__(
        self,
        item: Item,
        obj: Item | Item._AsTypeWrapper,
        show_at_begin: bool = True,
        hide_at_end: bool = False,
        **kwargs
    ):
        super().__init__(item, item, **kwargs)
        self.obj = obj
        self.show_at_begin = show_at_begin
        self.hide_at_end = hide_at_end
        self.delayed_actions: list[tuple[MethodTransform._ActionType, str | tuple[tuple, dict]]] = []

    def __getattr__(self, name: str):
        self.delayed_actions.append((MethodTransform._ActionType.GetAttr, name))
        return self

    def __call__(self, *args, **kwargs):
        self.delayed_actions.append((MethodTransform._ActionType.Call, (args, kwargs)))
        return self

    def _time_fixed(self) -> None:
        obj = self.obj
        for type, value in self.delayed_actions:
            if type is MethodTransform._ActionType.GetAttr:
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
    """
    使得 ``.anim`` 和 ``.anim(...)`` 后可以进行同样的操作
    """
    def __init__(self, item: Item):
        self.item = item
        self.obj = item._astype_wrapper or item

    def __call__(self, **kwargs):
        return MethodTransform(self.item, self.obj, **kwargs)

    def __getattr__(self, name):
        return getattr(MethodTransform(self.item, self.obj), name)


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
    # TODO: docs
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


@dataclass
class MatchingParams:
    src_center: np.ndarray
    target_center: np.ndarray


type MatchHandler = Callable[[VItem, VItem, MatchingParams, ], ItemAnimation]
type MismatchHandler = Callable[[VItem, MatchingParams, ], ItemAnimation]


class TransformMatchingShapes(AnimGroup):
    """
    匹配形状进行变换

    - ``match`` 表示对于匹配的形状的处理
    - ``mismatch`` 表示对于不匹配的形状的处理
    - 注：所有传入该动画类的额外参数（``**kwargs``）都会被传入 ``match`` 和 ``mismatch`` 的方法中

    .. janim-example:: TransformMatchingShapesExample
        :extract-from-test:
        :media: _static/videos/TransformMatchingShapesExample.mp4
        :url: https://janim.readthedocs.io/zh-cn/latest/janim/anims/transform.html#transformmatchingshapesexample
    """

    label_color = C_LABEL_ANIM_STAY

    def __init__(
        self,
        src: Item,
        target: Item,
        *,
        match: MatchHandler = lambda item1, item2, p, **kwargs: Transform(item1, item2, **kwargs),
        mismatch: tuple[MismatchHandler, MismatchHandler] = (
            lambda item, p, **kwargs: FadeOutToPoint(item, p.target_center, **kwargs),
            lambda item, p, **kwargs: FadeInFromPoint(item, p.src_center, **kwargs)
        ),
        duration: float = 2,
        lag_ratio: float = 0,
        collapse: bool = True,
        **kwargs
    ):
        src_mismatch_method, target_mismatch_method = mismatch
        kwargs['root_only'] = True  # 内层动画一定 root_only，否则处理带有子物件的非空图形会导致重复变换

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
        params = MatchingParams(src_center, target_center)

        super().__init__(
            *[
                match(piece1, piece2, params, **kwargs)
                for piece1, piece2 in zip(src_matched, target_matched)
            ],
            *[
                src_mismatch_method(piece, params, **kwargs)
                for piece in src_mismatched
            ],
            *[
                target_mismatch_method(piece, params, **kwargs)
                for piece in target_mismatched
            ],
            duration=duration,
            lag_ratio=lag_ratio,
            collapse=collapse
        )


class TransformMatchingDiff(AnimGroup):
    """
    匹配 diff 进行变换

    对于一般物件，使用形状匹配 diff；对于 :class:`~.Text` 使用 :class:`~.TextChar` 的字符匹配 diff

    - ``match`` 表示对于匹配的形状的处理
    - ``mismatch`` 表示对于不匹配的形状的处理
    - 注：所有传入该动画类的额外参数（``**kwargs``）都会被传入 ``match`` 和 ``mismatch`` 的方法中

    .. janim-example:: TransformMatchingDiffExample
        :extract-from-test-mark:
        :media: _static/videos/TransformMatchingDiffExample.mp4
        :url: https://janim.readthedocs.io/zh-cn/latest/janim/anims/transform.html#transformmatchingdiffexample
    """

    label_color = C_LABEL_ANIM_STAY

    def __init__(
        self,
        src: Item,
        target: Item,
        *,
        match: MatchHandler = lambda item1, item2, p, **kwargs: Transform(item1, item2, **kwargs),
        mismatch: tuple[MismatchHandler, MismatchHandler] = (
            lambda item, p, **kwargs: FadeOut(item, shift=p.target_center - p.src_center, **kwargs),
            lambda item, p, **kwargs: FadeIn(item, shift=p.target_center - p.src_center, **kwargs),
        ),
        duration: float = 2,
        lag_ratio: float = 0,
        collapse: bool = True,
        **kwargs
    ):
        src_mismatch_method, target_mismatch_method = mismatch
        kwargs['root_only'] = True  # 内层动画一定 root_only，否则处理带有子物件的非空图形会导致重复变换

        src_center = src(Points).points.box.center
        target_center = target(Points).points.box.center
        params = MatchingParams(src_center, target_center)

        a, b = self.get_match_sequences(src, target)
        matcher = difflib.SequenceMatcher(None, a, b)

        animations: list[ItemAnimation] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            match tag:
                case 'equal':
                    assert j2 - j1 == i2 - i1
                    animations += [
                        match(wrapper1.item, wrapper2.item, params, **kwargs)
                        for wrapper1, wrapper2 in zip(a[i1:i2], b[j1:j2])
                    ]

                case 'delete':
                    animations += [
                        src_mismatch_method(wrapper.item, params, **kwargs)
                        for wrapper in a[i1:i2]
                    ]

                case 'insert':
                    animations += [
                        target_mismatch_method(wrapper.item, params, **kwargs)
                        for wrapper in b[j1:j2]
                    ]

                case 'replace':
                    src_corners = np.vstack([
                        wrapper.item.points.self_box.get_corners()
                        for wrapper in a[i1:i2]
                    ])
                    target_corners = np.vstack([
                        wrapper.item.points.self_box.get_corners()
                        for wrapper in b[j1:j2]
                    ])

                    replace_params = MatchingParams(
                        Cmpt_Points.BoundingBox(src_corners).center,
                        Cmpt_Points.BoundingBox(target_corners).center
                    )

                    animations += [
                        src_mismatch_method(wrapper.item, replace_params, **kwargs)
                        for wrapper in a[i1:i2]
                    ]
                    animations += [
                        target_mismatch_method(wrapper.item, replace_params, **kwargs)
                        for wrapper in b[j1:j2]
                    ]

        super().__init__(
            *animations,
            duration=duration,
            lag_ratio=lag_ratio,
            collapse=collapse
        )

    @classmethod
    def get_match_sequences(
        cls,
        src: Item,
        target: Item
    ) -> tuple[list[_MatchWrapper], list[_MatchWrapper]]:

        def self_and_descendant_with_points(item: Item) -> list[VItem]:
            return [
                item
                for item in item.walk_self_and_descendants()
                if isinstance(item, VItem) and item.points.has()
            ]

        src_pieces = self_and_descendant_with_points(src)
        target_pieces = self_and_descendant_with_points(target)

        if cls.can_use_char_wrapper(src, target, src_pieces, target_pieces):
            wrapper_cls = cls._CharMatchWrapper
        else:
            wrapper_cls = cls._MatchWrapper

        return wrapper_cls.from_iterable(src_pieces), wrapper_cls.from_iterable(target_pieces)

    @staticmethod
    def can_use_char_wrapper(src: Item, target: Item, src_pieces: list[VItem], target_pieces: list[VItem]) -> bool:
        if not isinstance(src, (Text, TextLine, TextChar)):
            return False
        if not isinstance(target, (Text, TextLine, TextChar)):
            return False

        if not all(isinstance(piece, TextChar) for piece in src_pieces):
            return False
        if not all(isinstance(piece, TextChar) for piece in target_pieces):
            return False

        return True

    _map_to_hash_id: dict[int, int] = {}
    _next_hash_id = 0

    @dataclass
    class _MatchWrapper:
        item: VItem
        hash_id: int

        def __eq__(self, other: TransformMatchingDiff._MatchWrapper):
            return self.hash_id == other.hash_id

        def __hash__(self):
            return self.hash_id

        @classmethod
        def from_iterable(cls, iterable: Iterable):
            return [cls(x, cls.get_hash_id(x)) for x in iterable]

        @staticmethod
        def get_hash_id(x: VItem) -> int:
            """
            将 identity 的一组 hash 化归为单一 hash_id
            """
            map = TransformMatchingDiff._map_to_hash_id
            hashes = x.points.identity[0][:1]

            hash_id: int | None = None
            for h in hashes:
                recorded = map.get(h, None)
                if recorded is not None:
                    hash_id = recorded
                    break

            if hash_id is None:
                hash_id = TransformMatchingDiff._next_hash_id
                TransformMatchingDiff._next_hash_id += 1

            for h in hashes:
                map[h] = hash_id
            return hash_id

    @dataclass
    class _CharMatchWrapper(_MatchWrapper):
        item: TextChar

        def __eq__(self, other: TransformMatchingDiff._CharMatchWrapper):
            return self.item.char == other.item.char

        def __hash__(self):
            return hash(self.item.char)
