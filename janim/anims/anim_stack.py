from __future__ import annotations

from janim.anims.animation import Animation, TimeAligner
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

        # time_points 中 tuple 的 float 表示 list 的区段起始时间
        self.stacks: list[tuple[float, list[Animation]]] = [(0, [])]

    def detect_change(self, item: Item, at: float) -> None:
        '''
        检查物件相比 ``self.prev_display`` 所记录的物件而言是否发生变化

        若有变化则记录为 :class:`Display` 对象
        '''
        if self.prev_display is None or not self.prev_display.data.not_changed(item):
            anim = Display(item, item.store(), at=at, duration=FOREVER)
            self.time_aligner.align(anim)
            self.prev_display = anim
            # _time_fixed 会产生对 self.append 的调用，因此不用再另外 self.append
            anim._time_fixed()

    def append(self, anim: Animation) -> None:
        '''
        向 :class:`AnimStack` 添加 :class:`~.Animation` 对象
        '''  # 下面这些代码主要是为了对区段进行优化处理，减少调用 get_item 的复杂度
        stack_cnt = len(self.stacks)
        at = anim.t_range.at
        end = anim.t_range.end
        at_idx = None
        end_idx = stack_cnt if end is FOREVER else None
        # 在大多数情况中，anim 会被添加到末尾的区段
        # 所以这里从末尾开始遍历，而不是 bisect 二分查找
        for i, (t, _) in enumerate(reversed(self.stacks)):
            if end_idx is None:
                if t <= end:
                    # t_cnt - 1 - i 即 t 的下标
                    end_idx = stack_cnt - 1 - i
            if end_idx is not None:
                if t <= at:
                    at_idx = stack_cnt - 1 - i
                    break

        assert at_idx is not None
        assert end_idx is not None

        # 必要时在 at 处切一刀
        if self.stacks[at_idx][0] != at:
            at_idx += 1
            self.stacks.insert(at_idx, (at, self.stacks[at_idx - 1][1].copy()))
            end_idx += 1

        # 必要时在 end 处切一刀
        if end_idx != len(self.stacks) and self.stacks[end_idx][0] != end:
            end_idx += 1
            self.stacks.insert(end_idx, (end, self.stacks[end_idx - 1][1].copy()))

        # 如果 _cover_previous_anims=True，则替换覆盖
        # 否则，分别 append 到范围内的 stack 中
        if anim._cover_previous_anims:
            del self.stacks[at_idx + 1: end_idx]    # 删掉多余的区段
            stack = self.stacks[at_idx][1]
            stack.clear()
            stack.append(anim)
        else:
            for idx in range(at_idx, end_idx):
                self.stacks[idx][1].append(anim)

    def get_item(self, as_time: float) -> Item:
        pass
