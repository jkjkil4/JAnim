
from janim.anims.animation import Animation
from janim.utils.rate_functions import RateFunc, linear


class AnimGroup(Animation):
    '''
    动画集合（并列执行）

    - 若不传入 ``duration``，则将终止时间（子动画结束时间的最大值）作为该动画集合的 ``duration``
    - 若传入 ``duration``，则会将子动画的时间进行拉伸，使得终止时间与 ``duration`` 一致
    - 且可以使用 ``at`` 进行总体偏移（如 ``at=1`` 则是总体延后 1s）

    时间示例：

    .. code-block:: python

        AnimGroup(
            Anim1(duration=3),
            Anim2(duration=4)
        ) # Anim1 在 0~3s 执行，Anim2 在 0~4s 执行

        AnimGroup(
            Anim1(duration=3),
            Anim2(duration=4),
            duration=6
        ) # Anim1 在 0~4.5s 执行，Anim2 在 0~6s 执行

        AnimGroup(
            Anim1(duration=3),
            Anim2(duration=4),
            at=1,
            duration=6
        ) # Anim1 在 1~5.5s 执行，Anim2 在 1~7s 执行
    '''
    def __init__(
        self,
        *anims: Animation,
        duration: float | None = None,
        rate_func: RateFunc = linear,
        **kwargs
    ):
        self.anims = anims
        self.maxt = 0 if not anims else max(anim.local_range.end for anim in anims)
        if duration is None:
            duration = self.maxt

        super().__init__(duration=duration, rate_func=rate_func, **kwargs)

    def set_global_range(self, at: float, duration: float | None = None) -> None:
        '''
        设置并计算子动画的时间范围

        不需要手动设置，该方法是被 :meth:`~.Timeline.prepare` 调用以计算的
        '''
        super().set_global_range(at, duration)

        if duration is None:
            duration = self.local_range.duration

        factor = duration / self.maxt

        for anim in self.anims:
            anim.set_global_range(
                self.global_range.at + anim.local_range.at * factor,
                anim.local_range.duration * factor
            )

    def anim_on_alpha(self, alpha: float) -> None:
        '''
        在该方法中，:class:`AnimGroup` 通过 ``alpha``
        换算出子动画的 ``local_t`` 并调用子动画的 :meth:`~.Animation.anim_on` 方法
        '''
        adjusted_local_t = alpha * self.maxt

        for anim in self.anims:
            anim_t = adjusted_local_t - anim.local_range.at
            if 0 <= anim_t < anim.local_range.duration:
                anim.anim_on(anim_t)


class Succession(AnimGroup):
    '''
    动画集合（顺序执行）

    - 会将传入的动画依次执行，不并行
    - 可以传入 `buff` 指定前后动画中间的空白时间
    - 其余与 `AnimGroup` 相同

    时间示例：

    .. code-block:: python

        Succession(
            Anim1(duration=3),
            Anim2(duration=4)
        ) # Anim1 在 0~3s 执行，Anim2 在 3~7s 执行

        Succession(
            Anim1(duration=2),
            Anim2(at=1, duration=2),
            Anim3(at=0.5, duration=2)
        ) # Anim1 在 0~2s 执行，Anim2 在 3~5s 执行，Anim3 在 5.5~7.5s 执行

        Succession(
            Anim1(duration=2),
            Anim2(duration=2),
            Anim3(duration=2),
            buff=0.5
        ) # Anim1 在 0~2s 执行，Anim2 在 2.5~4.5s 执行，Anim3 在 5~7s 执行
    '''
    def __init__(self, *anims: Animation, buff: float = 0, **kwargs):
        end_time = 0
        for anim in anims:
            anim.local_range.at += end_time
            end_time = anim.local_range.end + buff
        super().__init__(*anims, **kwargs)


class Aligned(AnimGroup):
    '''
    动画集合（并列对齐执行）

    时间示例：

    .. code-block:: python

        Aligned(
            Anim1(duration=1),
            Anim2(duration=2)
        ) # Anim1 和 Anim2 都在 0~2s 执行

        Aligned(
            Anim1(duration=1),
            Anim2(duration=2),
            duration=4
        ) # Anim1 和 Anim2 都在 0~4s 执行
    '''
    def __init__(*anims: Animation, **kwargs):
        maxt = max(anim.local_range.end for anim in anims)
        for anim in anims:
            factor = anim.local_range.end / maxt
            anim.local_range.at *= factor
            anim.local_range.duration *= factor

        super().__init__(*anims, **kwargs)
