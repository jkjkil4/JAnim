
from typing import Callable

from janim.animation.animation import Animation
from janim.utils.rate_functions import linear, outside_linear_rate_func
from janim.utils.functions import safe_call_same

class _AbstractAnimationGroup(Animation):
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

        local_elapsed = elapsed - self.begin_time
        adjusted_elapsed = self.run_time * outside_linear_rate_func(self.rate_func)(local_elapsed / self.run_time)

        for anim in self.anims:
            anim.update(adjusted_elapsed, dt)
    
    def finish_all(self) -> None:
        for anim in self.anims:
            anim.finish_all()
        super().finish_all()

class AnimationGroup(_AbstractAnimationGroup):
    def __init__(
        self, 
        *anims: Animation, 
        run_time: float = None, 
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
