from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import defaultdict
from typing import Generator

from janim.anims.animation import ApplyAligner, ItemAnimation, StackableAnimation
from janim.anims.display import Display
from janim.anims_core.time import FOREVER, TimeAligner
from janim.exception import ApplyAlignerBrokenError
from janim.items.item import Item
from janim.locale import get_translator

type ComputeAnimsGenerator = Generator[ApplyAligner, None, Item]

_ = get_translator('janim.anims.anim_stack')


class OldAnimStack:
    """
    用于在 :class:`~.Timeline` 中记录作用于 :class:`~.Item` 上的 :class:`~.Animation`
    """

    def __init__(self, item: Item, time_aligner: TimeAligner):
        self.item = item
        self.time_aligner = time_aligner

        # 在跟踪物件变化时，该变量用于对比物件与先前记录的 Display 对象进行对比
        # 如果发生变化，则记录新的 Display 对象
        self.prev_display: Display | None = None

        # times 和 stacks 的元素是一一对应的
        # times 中的元素表示 stacks 中对应位置动画序列的开始时间（以下一个时间点为结束时间）
        self.times: list[float] = [0]
        self.stacks: list[list[ItemAnimation]] = [[]]

        # 用于缓存结果，具体处理另见 compute 方法
        self.clear_cache()

    def compute(self, as_time: float, readonly: bool, *, get_at_left: bool = False) -> None:
        """
        得到指定时间 ``as_time`` 的物件，考虑了动画的作用

        ``readonly`` 用来表示调用方是否会对返回值进行修改

        - 如果 ``readonly=True`` 则表示不会进行修改，该方法会放心地直接返回缓存
          （但是这并没有强制约束性，传入 ``readonly=True`` 时请遵循不修改返回值的原则，以免影响缓存数据）

        - 如果 ``readonly=False`` 则表示会进行修改，此时会返回缓存的拷贝，避免影响缓存数据

        例如：

        - :meth:`~.Timeline.item_current` 中的调用是 ``readonly=False`` 的，
          因为 :meth:`~.Timeline.item_current` 的返回值最终会被用户使用，我们不能保证用户是否会修改，所以我们干脆假定用户会修改

        - 例如用于绘制时的调用时 ``readonly=True``，因为绘制时不会对物件数据产生影响
        """
        anims = (self.get_at_left if get_at_left else self.get)(as_time)
        generator = OldAnimStack.compute_anims(self, as_time, anims)

        try:
            aligner = next(generator)
        except StopIteration as e:
            self._cache_time = as_time
            self._cache_data = e.value
        else:
            type Stacks = list[OldAnimStack]
            type Computing = dict[OldAnimStack, tuple[ComputeAnimsGenerator, ApplyAligner]]
            computing: Computing = {self: (generator, aligner)}
            stacks_map: dict[int, Stacks] = {}

            def append_stacks(stacks: Stacks) -> None:
                stacks_map[id(stacks)] = stacks
                for stack in stacks:
                    if stack in computing:
                        continue
                    anims = (stack.get_at_left if get_at_left else stack.get)(as_time)
                    generator = OldAnimStack.compute_anims(stack, as_time, anims)
                    # 一般情况下 next(generator) 不会触发 StopIteration
                    # 但是当 GroupUpdater 中的部分物件的动画栈被覆盖性动画覆盖后（例如 .anim 或者未传入 become_at_end 的 Updater）
                    # 就会触发 StopIteration，此时给出报错
                    try:
                        aligner = next(generator)
                    except StopIteration:
                        raise ApplyAlignerBrokenError(
                            _(
                                'The GroupUpdater structure was broken by an overriding animation, '
                                'possibly caused by .anim or by an Updater '
                                'that ended earlier without passing become_at_end=False'
                            )
                        )
                    else:
                        computing[stack] = (generator, aligner)
                        if id(aligner.stacks) not in stacks_map:
                            append_stacks(aligner.stacks)

            append_stacks(aligner.stacks)

            while computing:
                counter: defaultdict[int, int] = defaultdict(int)
                for stack, (generator, aligner) in computing.items():
                    sid = id(aligner.stacks)
                    counter[sid] += 1
                    if counter[sid] == len(aligner.stacks):
                        stacks_found = aligner.stacks
                        break
                else:
                    assert False

                iterates = [
                    (stack, generator)
                    for stack, (generator, _) in computing.items()
                    if stack in stacks_found  #
                ]

                drop: list[OldAnimStack] = []

                for stack, generator in iterates:
                    try:
                        aligner = next(generator)
                        computing[stack] = (generator, aligner)
                    except StopIteration as e:
                        drop.append(stack)
                        stack._cache_time = as_time
                        stack._cache_data = e.value
                    else:
                        if id(aligner.stacks) not in stacks_map:
                            append_stacks(aligner.stacks)

                computing = {
                    stack: tup
                    for stack, tup in computing.items()
                    if stack not in drop  #
                }

    def compute_anims(self, as_time: float, anims: list[ItemAnimation]) -> ComputeAnimsGenerator:
        if not anims:
            return self.item

        params = StackableAnimation.ApplyParams(as_time, anims, 0)

        for i, anim in enumerate(anims):
            if i == 0:
                data = anim.apply(None, params)
            else:
                if isinstance(anim, ApplyAligner):
                    anim.pre_apply(data, params)
                    yield anim
                params.index = i
                anim.apply(data, params)

        return data

    def clear_cache(self) -> None:
        self._cache_time: float | None = None
        self._cache_data: Item | None = None
