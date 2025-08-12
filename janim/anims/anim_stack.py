from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import defaultdict
from typing import Generator

from janim.anims.animation import ApplyAligner, ItemAnimation, TimeAligner
from janim.anims.display import Display
from janim.constants import FOREVER
from janim.exception import ApplyAlignerBrokenError
from janim.items.item import Item
from janim.locale.i18n import get_local_strings

type ComputeAnimsGenerator = Generator[ApplyAligner, None, Item]

_ = get_local_strings('anim_stack')


class AnimStack:
    '''
    用于在 :class:`~.Timeline` 中记录作用于 :class:`~.Item` 上的 :class:`~.Animation`
    '''
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

    def detect_change(self, item: Item, at: float, *, force: bool = False) -> None:
        '''
        检查物件相比 ``self.prev_display`` 所记录的物件而言是否发生变化

        若有变化则记录为 :class:`Display` 对象
        '''
        if self.prev_display is None:
            at = 0
        if self.prev_display is None or force or not self.prev_display.data_orig.not_changed(item):
            anim = Display(item, item.store(), at=at, duration=FOREVER, show_at_begin=False)
            # finalize 会产生对 self.append 的调用，因此不用再另外 self.append
            anim.finalize()
            self.prev_display = anim

    def has_detected_change(self) -> bool:
        return self.prev_display is not None

    def detect_change_if_not(self, item: Item) -> None:
        if not self.has_detected_change():
            self.detect_change(item, 0)

    def append(self, anim: ItemAnimation) -> None:
        '''
        向 :class:`AnimStack` 添加 :class:`~.Animation` 对象
        '''

        # 下面这些代码主要是为了对区段进行优化处理，提前计算出特定区段中存在哪些动画对象
        # 这样可以避免在 compute 以及渲染时重复判断哪些动画对象是否作用，提高效率

        #
        t_cnt = len(self.times)
        at = anim.t_range.at
        end = anim.t_range.end
        at_idx = None
        end_idx = t_cnt if end is FOREVER else None

        # 避免缓存导致的问题
        if self.cache_time is not None:
            self.clear_cache()

        # 在大多数情况中，anim 会被添加到末尾的区段
        # 所以这里从末尾开始遍历，而不是 bisect 二分查找
        for i, t in enumerate(reversed(self.times)):
            if end_idx is None:
                if t <= end:
                    # t_cnt - 1 - i 即 t 的下标
                    end_idx = t_cnt - 1 - i
            if end_idx is not None:
                if t <= at:
                    at_idx = t_cnt - 1 - i
                    break

        assert at_idx is not None
        assert end_idx is not None

        # 必要时在 at 处切一刀
        if self.times[at_idx] != at:
            at_idx += 1
            self.times.insert(at_idx, at)
            self.stacks.insert(at_idx, self.stacks[at_idx - 1].copy())
            end_idx += 1

        # 必要时在 end 处切一刀
        if end_idx != len(self.times) and self.times[end_idx] != end:
            end_idx += 1
            self.times.insert(end_idx, end)
            self.stacks.insert(end_idx, self.stacks[end_idx - 1].copy())

        # 如果 _cover_previous_anims=True，则替换覆盖
        # 否则，分别 append 到范围内的 stack 中
        # 关于标记 _cover_previous_anims 的动机，可以参阅该变量在 ItemAnimation 中的声明
        if anim._cover_previous_anims:
            if at_idx + 1 != end_idx:
                # 删掉多余的区段
                del self.times[at_idx + 1: end_idx]
                del self.stacks[at_idx + 1: end_idx]
            stack = self.stacks[at_idx]
            stack.clear()
            stack.append(anim)
        else:
            for idx in range(at_idx, end_idx):
                self.stacks[idx].append(anim)

    def get_at_left(self, as_time: float) -> list[ItemAnimation]:
        idx = bisect_left(self.times, as_time) - 1
        return self.stacks[max(0, idx)]

    def get(self, as_time: float) -> list[ItemAnimation]:
        idx = bisect_right(self.times, as_time) - 1
        assert idx >= 0
        return self.stacks[idx]

    def compute(self, as_time: float, readonly: bool, *, get_at_left: bool = False) -> Item:
        '''
        得到指定时间 ``as_time`` 的物件，考虑了动画的作用

        ``readonly`` 用来表示调用方是否会对返回值进行修改

        - 如果 ``readonly=True`` 则表示不会进行修改，该方法会放心地直接返回缓存
          （但是这并没有强制约束性，传入 ``readonly=True`` 时请遵循不修改返回值的原则，以免影响缓存数据）

        - 如果 ``readonly=False`` 则表示会进行修改，此时会返回缓存的拷贝，避免影响缓存数据

        例如：

        - :meth:`~.Timeline.item_current` 中的调用是 ``readonly=False`` 的，
          因为 :meth:`~.Timeline.item_current` 的返回值最终会被用户使用，我们不能保证用户是否会修改，所以我们干脆假定用户会修改

        - 例如用于绘制时的调用时 ``readonly=True``，因为绘制时不会对物件数据产生影响
        '''
        if as_time != self.cache_time:
            anims = (self.get_at_left if get_at_left else self.get)(as_time)
            generator = self.compute_anims(as_time, anims)

            try:
                aligner = next(generator)
            except StopIteration as e:
                self.cache_time = as_time
                self.cache_data = e.value
            else:
                type Stacks = list[AnimStack]
                type Computing = dict[AnimStack, tuple[ComputeAnimsGenerator, ApplyAligner]]
                computing: Computing = {self: (generator, aligner)}
                stacks_map: dict[int, Stacks] = {}

                def append_stacks(stacks: Stacks) -> None:
                    stacks_map[id(stacks)] = stacks
                    for stack in stacks:
                        if stack in computing:
                            continue
                        anims = (stack.get_at_left if get_at_left else stack.get)(as_time)
                        generator = stack.compute_anims(as_time, anims)
                        # 一般情况下 next(generator) 不会触发 StopIteration
                        # 但是当 GroupUpdater 中的部分物件的动画栈被覆盖性动画覆盖后（例如 .anim 或者未传入 become_at_end 的 Updater）
                        # 就会触发 StopIteration，此时给出报错
                        try:
                            aligner = next(generator)
                        except StopIteration:
                            raise ApplyAlignerBrokenError(
                                _('The GroupUpdater structure was broken by an overriding animation, '
                                  'possibly caused by .anim or by an Updater '
                                  'that ended earlier without passing become_at_end=False')
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
                        if stack in stacks_found
                    ]

                    drop: list[AnimStack] = []

                    for stack, generator in iterates:
                        try:
                            aligner = next(generator)
                            computing[stack] = (generator, aligner)
                        except StopIteration as e:
                            drop.append(stack)
                            stack.cache_time = as_time
                            stack.cache_data = e.value
                        else:
                            if id(aligner.stacks) not in stacks_map:
                                append_stacks(aligner.stacks)

                    computing = {
                        stack: tup
                        for stack, tup in computing.items()
                        if stack not in drop
                    }

        return self.cache_data if readonly else self.cache_data.store()

    def compute_anims(self, as_time: float, anims: list[ItemAnimation]) -> ComputeAnimsGenerator:
        if not anims:
            return self.item

        params = ItemAnimation.ApplyParams(as_time, anims, 0)

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
        self.cache_time: float | None = None
        self.cache_data: Item | None = None
