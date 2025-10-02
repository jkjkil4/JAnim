from typing import Iterable, Self

from janim.anims.animation import Animation, TimeAligner
from janim.exception import AnimGroupError, NotAnimationError
from janim.locale.i18n import get_local_strings
from janim.typing import SupportsAnim
from janim.utils.rate_functions import RateFunc, linear

_ = get_local_strings('composition')


class AnimGroup(Animation):
    '''
    动画集合（并列执行）

    - 若不传入 ``duration``，则将终止时间（子动画结束时间的最大值）作为该动画集合的 ``duration``
    - 若传入 ``duration``，则会将子动画的生效时间进行拉伸，使得总终止时间与 ``duration`` 一致
    - 且可以使用 ``at`` 进行总体偏移（如 ``at=1`` 则是总体延后 1s）

    可以使用 ``lag_ratio`` 和 ``offset`` 控制每个子动画相对于前一个子动画的时间位置：

    - ``lag_ratio`` 表示 “前一个进行到百分之多少时，进行下一个”
    - ``offset`` 表示 “前一个进行多少秒后，进行下一个”

    时间示例：

    .. code-block:: python

        AnimGroup(
            Anim1(duration=3),  # 0~3s
            Anim2(duration=4)   # 0~4s
        )

        AnimGroup(
            Anim1(duration=3),  # 0~4.5s
            Anim2(duration=4),  # 0~6s
            duration=6
        )

        AnimGroup(
            Anim1(duration=3),  # 1~5.5s
            Anim2(duration=4),  # 1~7s
            at=1,
            duration=6
        )

    另外，``collapse`` 表示在预览界面中是否折叠该动画组（默认不折叠，而例如 :class:`~.TransfromMatchingShapes` 默认是折叠的）
    '''
    def __init__(
        self,
        *anims: SupportsAnim,
        at: float = 0,
        duration: float | None = None,
        lag_ratio: float = 0,
        offset: float = 0,
        rate_func: RateFunc = linear,
        name: str | None = None,
        collapse: bool = False,
    ):
        self.anims = self._get_anim_objects(anims)
        for anim in self.anims:
            anim.parent = self

        self.collapse = collapse
        self._adjust_t_range(lag_ratio, offset)

        if not self.anims:
            duration = 0
        else:
            # 对于一个 AnimGroup 而言：
            #   如果它的子动画不对齐（对齐：即每个都 at=0，并且 end 相同）
            #   如果它的子动画中有 _is_aligned=False
            # 那么认为父动画 _is_aligned=False
            end = self.anims[0].t_range.num_end
            self.is_aligned = all(
                anim.is_aligned
                and anim.t_range.at == 0
                and anim.t_range.num_end == end

                for anim in self.anims
            )

            # 如果子动画是不对齐的，作用在该 AnimGroup 上的非线性 rate-func 会有意外的结果
            # 在 JAnim 2 及之前是警告，在 JAnim 3 之后改为了报错
            # 如果要解决这个问题，需要求 rate-func 的反函数，在设计和效果上不太理想
            #
            # 并且改为报错后，也方便对 rate-func 的处理进行优化
            # 具体来说，在之前的计算中，子动画插值依赖于父 AnimGroup 的传递
            # 更改后，子动画插值不需要由父 AnimGroup 传递
            # 并且让 AnimGroup 的作用弱化为了“通过 at, duration, lag_ratio, offfset 等参数影响子动画的区间”
            if rate_func is not linear:
                if not self.is_aligned:
                    raise AnimGroupError(_('Passing misaligned sub-animations to a composition '
                                           'with non-linear rate_func is not allowed'))
                for anim in self.anims:
                    anim._attach_rate_func(rate_func)

            # duration 对子动画区段的拉伸作用
            maxt = max(anim.t_range.num_end for anim in self.anims)
            if duration is None:
                duration = maxt
            else:
                if maxt != 0 and maxt != duration:
                    factor = duration / maxt
                    for anim in self.anims:
                        anim.scale_range(factor)

            # at 对子动画区段的偏移作用
            if at != 0:
                for anim in self.anims:
                    anim.shift_range(at)

        super().__init__(at=at, duration=duration, rate_func=rate_func, name=name)

    def _adjust_t_range(self, lag_ratio: float, offset: float) -> None:
        '''
        对于 :class:`AnimGroup` 和 :class:`Succession` 而言
        是应用 ``lag_ratio`` 和 ``offset`` 的效果

        而对于 :class:`Aligned` 而言会被重载
        '''
        if lag_ratio != 0 or offset != 0:
            start = 0
            global_offset = 0

            # 将 lag_ratio 和 offset 应用到每个子动画上
            for anim in self.anims:
                anim.shift_range(start)
                if anim.t_range.at < 0:
                    global_offset = max(global_offset, -anim.t_range.at)
                start = anim.t_range.at + lag_ratio * anim.t_range.num_duration + offset

            # 如果 lag_ratio 或者 offset 很小（一般指负数的情况），会导致后一个动画比前一个还早
            # 这时候需要将整体向后偏移使得与最早的那个对齐
            if global_offset != 0:
                for anim in self.anims:
                    anim.shift_range(global_offset)

    @staticmethod
    def _get_anim_objects(anims: Iterable[SupportsAnim]) -> list[Animation]:
        '''
        将 anims 中的内容都转化为 :class:`~.Animation`
        具体可参考 :class:`SupportsAnim` 的文档
        '''
        return [
            AnimGroup._get_anim_object(anim)
            for anim in anims
        ]

    @staticmethod
    def _get_anim_object(anim: SupportsAnim) -> Animation:
        attr = getattr(anim, '__anim__', None)
        if attr is None:
            raise NotAnimationError(_('A non-animation object was passed in, '
                                      'you might have forgotten to use .anim'))
        return attr()

    def shift_range(self, delta: float) -> Self:
        super().shift_range(delta)
        for anim in self.anims:
            anim.shift_range(delta)
        return self

    def scale_range(self, k: float) -> Self:
        super().scale_range(k)
        for anim in self.anims:
            anim.scale_range(k)
        return self

    def _attach_rate_func(self, rate_func: RateFunc) -> None:
        super()._attach_rate_func(rate_func)
        for anim in self.anims:
            anim._attach_rate_func(rate_func)

    def _align_time(self, aligner: TimeAligner):
        super()._align_time(aligner)
        for anim in self.anims:
            anim._align_time(aligner)

    def _time_fixed(self) -> None:
        for anim in self.anims:
            anim._time_fixed()


class Succession(AnimGroup):
    '''
    动画集合（顺序执行）

    - 会将传入的动画依次执行
    - 相当于默认值 ``lag_ratio=1`` 的 :class:`~.AnimGroup`

    时间示例：

    .. code-block:: python

        Succession(
            Anim1(duration=3),  # 0~3s
            Anim2(duration=4)   # 3~7s
        )

        Succession(
            Anim1(duration=2),          # 0~2s
            Anim2(at=1, duration=2),    # 3~5s
            Anim3(at=0.5, duration=2)   # 5.5~7.5s
        )

        Succession(
            Anim1(duration=2),  # 0~2s
            Anim2(duration=2),  # 2.5~4.5s
            Anim3(duration=2),  # 5~7s
            offset=0.5
        )
    '''
    def __init__(
        self,
        *anims: Animation,
        lag_ratio: float = 1,
        offset: float = 0,
        **kwargs
    ):
        super().__init__(*anims, lag_ratio=lag_ratio, offset=offset, **kwargs)


class Aligned(AnimGroup):
    '''
    动画集合（并列对齐执行）

    也就是忽略了子动画的 ``at`` 和 ``duration``，使所有子动画都一起开始和结束

    时间示例：

    .. code-block:: python

        Aligned(
            Anim1(duration=1),
            Anim2(duration=2)
        )
        # Anim1 & Anim2: 0~2s

        Aligned(
            Anim1(at=1, duration=1),
            Anim2(duration=2),
            duration=4
        )
        # Anim1 & Anim2: 0~4s
    '''
    def __init__(
        self,
        *anims: SupportsAnim,
        at: float = 0,
        duration: float | None = None,
        rate_func: RateFunc = linear,
        name: str | None = None,
        collapse: bool = False,
    ):
        super().__init__(*anims, at=at, duration=duration, rate_func=rate_func, name=name, collapse=collapse)

    def _adjust_t_range(self, lag_ratio, offset):
        end = max(anim.t_range.num_end for anim in self.anims)
        for anim in self.anims:
            anim.shift_range(-anim.t_range.at)
            anim.scale_range(end / anim.t_range.num_end)


class Wait(Animation):
    '''
    等待特定时间，在 :meth:`~.Succession` 中比较有用

    （其实就是一个空动画）
    '''
    def __init__(self, duration: float = 1, **kwargs):
        super().__init__(duration=duration, **kwargs)


class Do(Animation):
    '''
    在动画的特定时间执行指定操作
    '''
    def __init__(self, func, *args, at: float = 0, detect_changes: bool = True, **kwargs):
        super().__init__(at=at, duration=0)
        self.func = func
        self.args = args
        self.detect_changes = detect_changes
        self.kwargs = kwargs

    def _time_fixed(self) -> None:
        if self.detect_changes:
            self.timeline.schedule_and_detect_changes(self.t_range.at, self.func, *self.args, **self.kwargs)
        else:
            self.timeline.schedule(self.t_range.at, self.func, *self.args, **self.kwargs)
