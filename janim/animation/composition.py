
from typing import Callable, Optional

from janim.animation.animation import Animation
from janim.utils.rate_functions import linear, outside_linear_rate_func

class _AbstractAnimationGroup(Animation):
    '''
    动画集合的基类，
    用于包含其他 `Animation` 对象
    '''
    def __init__(
        self,
        *anims: Animation, 
        rate_func: Callable[[float], float] = linear, 
        **kwargs
    ) -> None:
        super().__init__(rate_func=rate_func, **kwargs)
        self.anims = anims

    def update(self, elapsed, dt) -> None:
        super().update(elapsed, dt)

        # 计算出相对于当前动画集合的持续时间，也就是要扣去 `begin_time`
        local_elapsed = elapsed - self.begin_time
        # 对持续时间应用 `rate_func`，做到整体插值的目的
        adjusted_elapsed = self.run_time * outside_linear_rate_func(self.rate_func)(local_elapsed / self.run_time)

        for anim in self.anims:
            anim.update(adjusted_elapsed, dt)
    
    def finish_all(self) -> None:
        '''
        传递 `finish_all`，
        保证所有子动画都进入 `AfterExec` 状态
        '''
        for anim in self.anims:
            anim.finish_all()
        super().finish_all()

class AnimationGroup(_AbstractAnimationGroup):
    '''
    动画集合（并列执行）

    - 若不传入 `run_time`，则将终止时间（子动画中 `begin_time + run_time` 中的最大值）作为该动画集合的 `run_time`
    - 若传入 `run_time`，则会将子动画的时间进行拉伸，使得终止时间与 `run_time` 一致
    - 且可以使用 `begin_time` 进行总体偏移（如 `begin_time=1` 则是总体延后 1s）

    时间示例：
    ```python
    AnimationGroup(
        Anim1(run_time=3),
        Anim2(run_time=4)
    ) # Anim1 在 0~3s 执行，Anim2 在 0~4s 执行

    AnimationGroup(
        Anim1(run_time=3),
        Anim2(run_time=4),
        run_time=6
    ) # Anim1 在 0~4.5s 执行，Anim2 在 0~6s 执行

    AnimationGroup(
        Anim1(run_time=3),
        Anim2(run_time=4),
        run_time=6,
        begin_time=1
    ) # Anim1 在 1~5.5s 执行，Anim2 在 1~7s 执行
    ```
    '''
    def __init__(
        self, 
        *anims: Animation, 
        run_time: Optional[float] = None, 
        **kwargs
    ) -> None:
        maxt = max([anim.begin_time + anim.run_time for anim in anims])
        if run_time is None:
            run_time = maxt
        else:
            factor = run_time / maxt
            for anim in anims:
                anim.begin_time *= factor
                anim.run_time *= factor
        super().__init__(*anims, run_time=run_time, **kwargs)


# TODO: Succession
