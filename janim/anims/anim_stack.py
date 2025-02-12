from __future__ import annotations

from bisect import bisect

from janim.anims.animation import QUERY_OFFSET, ItemAnimation, TimeAligner
from janim.anims.display import Display
from janim.constants import FOREVER
from janim.items.item import Item


class AnimStack:
    '''
    用于在 :class:`~.Timeline` 中记录作用于 :class:`~.Item` 上的 :class:`~.Animation`

    :class:`~.Timeline` 构造结束后会自动调用 :meth:`finalize` 确定动画调用序列以优化性能
    '''
    def __init__(self, time_aligner: TimeAligner):
        self.time_aligner = time_aligner

        # 在跟踪物件变化时，该变量用于对比物件与先前记录的 Display 对象进行对比
        # 如果发生变化，则记录新的 Display 对象
        self.prev_display: Display | None = None

        # times 和 stacks 的元素是一一对应的
        # times 中的元素表示 stacks 中对应位置动画序列的开始时间（以下一个时间点为结束时间）
        self.times: list[float] = [0]
        self.stacks: list[list[ItemAnimation]] = [[]]

        # 用于缓存结果，具体处理另见 compute 方法
        self.cache_time: float | None = None
        self.cache_data: Item | None = None

    def detect_change(self, item: Item, at: float) -> None:
        '''
        检查物件相比 ``self.prev_display`` 所记录的物件而言是否发生变化

        若有变化则记录为 :class:`Display` 对象
        '''
        if self.prev_display is None:
            at = 0
        if self.prev_display is None or not self.prev_display.data.not_changed(item):
            anim = Display(item, item.store(), at=at, duration=FOREVER)
            self.time_aligner.align(anim)
            self.prev_display = anim
            # _time_fixed 会产生对 self.append 的调用，因此不用再另外 self.append
            anim._time_fixed()

    def has_detected_change(self) -> bool:
        return self.prev_display is not None

    def append(self, anim: ItemAnimation) -> None:
        '''
        向 :class:`AnimStack` 添加 :class:`~.Animation` 对象
        '''
        # 下面这些代码主要是为了对区段进行优化处理，提前计算出特定区段中存在哪些动画对象
        # 这样可以避免在 compute 以及渲染时重复判断哪些动画对象是否作用，提高效率
        t_cnt = len(self.times)
        at = anim.t_range.at
        end = anim.t_range.end
        at_idx = None
        end_idx = t_cnt if end is FOREVER else None
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
        # 关于标记 _cover_previous_anims 的动机，可以参阅该变量在 Animation 中的声明
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

    def compute(self, as_time: float, readonly: bool) -> Item:
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
        if as_time == self.cache_time:
            data = self.cache_data
        else:
            self.cache_time = as_time

            # 计算作用动画后的数据
            idx = bisect(self.times, as_time + QUERY_OFFSET) - 1
            assert idx >= 0

            anims = self.stacks[idx]

            if len(anims) == 1:
                # 只有一个动画，可以认为它是 Display 对象
                # 因为它没有后继动画，所以直接使用 .data_orig 作为结果，而不调用 .apply
                anims: list[Display]
                data = anims[0].data_orig
            else:
                params = ItemAnimation.ApplyParams(as_time, anims, 0)

                for i, anim in enumerate(anims):
                    if i == 0:
                        data = anim.apply(None, params)
                    else:
                        params.index = i
                        anim.apply(data, params)

            self.cache_data = data

        return data if readonly else data.store()
