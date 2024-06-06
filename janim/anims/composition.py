from janim.anims.animation import Animation
from janim.exception import NotAnimationError
from janim.locale.i18n import get_local_strings
from janim.utils.rate_functions import RateFunc, linear

_ = get_local_strings('composition')


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
        _get_anim_objects: bool = True,
        **kwargs
    ):
        if _get_anim_objects:
            anims = self._get_anim_objects(anims)
        self.anims = anims
        self.maxt = 0 if not anims else max(anim.local_range.end for anim in anims)
        if duration is None:
            duration = self.maxt

        super().__init__(duration=duration, rate_func=rate_func, **kwargs)
        for anim in self.anims:
            anim.parent = self

    @staticmethod
    def _get_anim_object(anim) -> Animation:
        attr = getattr(anim, '__anim__', None)
        if attr is not None and callable(attr):
            return attr()
        return anim

    @staticmethod
    def _get_anim_objects(anims: list[Animation]) -> list[Animation]:
        anims = [
            AnimGroup._get_anim_object(anim)
            for anim in anims
        ]
        for anim in anims:
            if not isinstance(anim, Animation):
                raise NotAnimationError(_('A non-animation object was passed in, '
                                          'you might have forgotten to use .anim'))

        return anims

    def flatten(self) -> list[Animation]:
        result = [self]
        for anim in self.anims:
            if isinstance(anim, AnimGroup):
                result.extend(anim.flatten())
            else:
                result.append(anim)

        return result

    def compute_global_range(self, at: float, duration: float) -> None:
        '''
        计算子动画的时间范围

        该方法是被 :meth:`~.Timeline.prepare` 调用以计算的
        '''
        super().compute_global_range(at, duration)

        if not self.anims:
            return

        factor = duration / self.maxt

        for anim in self.anims:
            anim.compute_global_range(
                self.global_range.at + anim.local_range.at * factor,
                anim.local_range.duration * factor
            )

    def anim_pre_init(self) -> None:
        for anim in self.anims:
            anim.anim_pre_init()

    def anim_init(self) -> None:
        for anim in self.anims:
            anim.anim_init()

    def get_anim_t(self, alpha: float, anim: Animation) -> float:
        return alpha * self.maxt - anim.local_range.at

    def anim_on_alpha(self, alpha: float) -> None:
        '''
        在该方法中，:class:`AnimGroup` 通过 ``alpha``
        换算出子动画的 ``local_t`` 并调用子动画的 :meth:`~.Animation.anim_on` 方法
        '''
        global_t = self.global_t_ctx.get()

        for anim in self.anims:
            anim_t = self.get_anim_t(alpha, anim)
            if anim.global_range.at <= global_t < anim.global_range.end:
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
        anims = self._get_anim_objects(anims)
        end_time = 0
        for anim in anims:
            anim.local_range.at += end_time
            end_time = anim.local_range.end + buff
        super().__init__(*anims, _get_anim_objects=False, **kwargs)


class Aligned(AnimGroup):
    '''
    动画集合（并列对齐执行）

    也就是忽略了子动画的 ``at`` 和 ``duration``，使所有子动画都一起开始和结束

    时间示例：

    .. code-block:: python

        Aligned(
            Anim1(duration=1),
            Anim2(duration=2)
        ) # Anim1 和 Anim2 都在 0~2s 执行

        Aligned(
            Anim1(at=1, duration=1),
            Anim2(duration=2),
            duration=4
        ) # Anim1 和 Anim2 都在 0~4s 执行
    '''
    def __init__(self, *anims: Animation, duration: float | None = None, **kwargs):
        anims = self._get_anim_objects(anims)
        if duration is None:
            duration = max(anim.local_range.end for anim in anims)

        super().__init__(*anims, duration=duration, _get_anim_objects=False, **kwargs)

    def compute_global_range(self, at: float, duration: float) -> None:
        Animation.compute_global_range(self, at, duration)

        for anim in self.anims:
            anim.compute_global_range(at, duration)

    def get_anim_t(self, alpha: float, anim: Animation) -> float:
        return alpha * anim.local_range.duration


class Wait(Animation):
    '''
    等待特定时间，在 :meth:`~.Succession` 中比较有用

    （其实就是一个空动画）
    '''
    def __init__(self, duration: float, **kwargs):
        super().__init__(duration=duration, **kwargs)
