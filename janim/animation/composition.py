
from janim.animation.animation import Animation
from janim.utils.rate_functions import RateFunc, linear, outside_linear_rate_func

class AnimationGroup(Animation):
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
        run_time: float | None = None,
        rate_func: RateFunc = linear, 
        **kwargs
    ) -> None:
        self.anims = anims
        self.maxt = max([anim.begin_time + anim.run_time for anim in anims])
        if run_time is None:
            run_time = self.maxt

        super().__init__(run_time=run_time, rate_func=rate_func, **kwargs)

    def set_scene_instance(self, scene) -> None:
        super().set_scene_instance(scene)
        for anim in self.anims:
            anim.set_scene_instance(scene)

    def update(self, elapsed, dt) -> None:
        super().update(elapsed, dt)

        # 计算出相对于当前动画集合的持续时间，也就是要扣去 `begin_time`
        local_elapsed = elapsed - self.begin_time
        # 对持续时间应用 `rate_func`，做到整体插值的目的
        adjusted_elapsed = self.maxt * outside_linear_rate_func(self.rate_func)(local_elapsed / self.run_time)

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

class Succession(AnimationGroup):
    '''
    动画集合（顺序执行）

    - 会将传入的动画依次执行，不并行
    - 可以传入 `buff` 指定前后动画中间的空白时间
    - 其余与 `AnimationGroup` 相同

    时间示例：
    ```python
    Succession(
        Anim1(run_time=3),
        Anim2(run_time=4)
    ) # Anim1 在 0~3s 执行，Anim2 在 3~7s 执行

    Succession(
        Anim1(run_time=2),
        Anim2(begin_time=1, run_time=2),
        Anim3(begin_time=0.5, run_time=2)
    ) # Anim1 在 0~2s 执行，Anim2 在 3~5s 执行，Anim3 在 5.5~7.5s 执行

    Succession(
        Anim1(run_time=2),
        Anim2(run_time=2),
        Anim3(run_time=2),
        buff=0.5
    ) # Anim1 在 0~2s 执行，Anim2 在 2.5~4.5s 执行，Anim3 在 5~7s 执行
    ```
    '''
    def __init__(self, *anims: Animation, buff: float = 0, **kwargs) -> None:
        end_time = 0
        for anim in anims:
            anim.begin_time += end_time
            end_time = anim.begin_time + anim.run_time + buff
        super().__init__(*anims, **kwargs)

class Aligned(AnimationGroup):
    '''
    动画集合（并列对齐执行）

    时间示例：
    ```python
    Aligned(
        Anim1(run_time=1),
        Anim2(run_time=2)
    ) # Anim1 和 Anim2 都在 0~2s 执行

    Aligned(
        Anim1(run_time=1),
        Anim2(run_time=2),
        run_time=4
    ) # Anim1 和 Anim2 都在 0~4s 执行
    ```
    '''
    def update(self, elapsed, dt) -> None:
        local_elapsed = elapsed - self.begin_time
        local_alpha = outside_linear_rate_func(self.rate_func)(local_elapsed / self.run_time)

        for anim in self.anims:
            end_time = anim.begin_time + anim.run_time
            adjusted_elapsed = end_time * local_alpha
            anim.update(adjusted_elapsed, dt)

