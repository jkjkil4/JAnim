from bisect import bisect_left, bisect_right
from janim.anims.animation import StackableAnimation
from janim.anims.display import Display
from janim.anims_core.time import FOREVER, TimeAligner
from janim.items.item import Item


class AnimStack:
    """
    用于记录作用于特定 :class:`~.Item` 上的 :class:`~.StackableAnimation`，形成一个堆栈

    JAnim 动画的核心逻辑：

    后一个动画，会以前一个动画的结果为基础，继续叠加作用

    这就是我们“动画复合”功能的内部逻辑，这个内部结构我们将其称作“动画堆栈”
    """

    def __init__(self, item: Item, time_aligner: TimeAligner):
        self.item = item
        self.time_aligner = time_aligner

        # _chunk_starts 和 _chunks 的元素总是一一对应的
        # _chunk_starts 中每个元素，都表示对应的 chunk 的开始时间（以下一个时间点为结束时间）
        # 注：为了方便直接 bisect，没有将他们打包为一个 dataclass，而是将他们各自存储为一个列表
        # 注：关于该算法策略的具体介绍，请参考 append 方法的说明
        self._chunk_starts: list[float] = [0]
        self._chunks: list[list[StackableAnimation]] = [[]]  # TODO: 放入初始状态

        # 直接调用 clear_cache 即可做到其变量的初始化，具体处理另见 compute 方法
        self.clear_cache()

        # 初始化，填入默认 Display，这里会初始化 _prev_display 变量
        # _prev_display 变量的含义即为先前记录的物件状态
        # Timeline 会在每次前进时间时 detect_change 检查物件，便可使用 _prev_display 作为比较基础
        self.display(0)

    def clear_cache(self) -> None:
        self._cache_time: float | None = None
        self._cache_data: Item | None = None

    # region modification

    def display(self, global_t: float) -> None:
        """
        将物件当前的状态记录到动画堆栈中，将 ``global_t`` 之后都显示为该状态
        """
        anim = Display(self.item.store(), at=global_t, duration=FOREVER)
        anim.finalize()
        self.append(anim)
        self._prev_display = anim

    def detect_change(self, global_t: float) -> None:
        """
        若物件相比 ``self._prev_display`` 所记录的状态可能有变化，
        则将新的状态记录到 ``global_t`` 之后的堆栈中
        """
        if self.may_changed():
            self.display(global_t)

    def may_changed(self) -> bool:
        """
        检查物件相比 ``self._prev_display`` 所记录的状态，是否可能发生变化
        """
        return not self._prev_display.data_orig.not_changed(self.item)

    def append(self, anim: StackableAnimation) -> None:
        """
        向堆栈添加一个 :class:`~.StackableAnimation` 对象

        :param anim: 要向堆栈添加的动画对象

        策略：

        首先，给出一个直观的理解，我们可以将时间轴看作一个条形的画布，颜料可以一直往上叠加，
        我们每使用该方法添加一个动画对象，就是根据动画时间的起止范围，在这个画布上画上一笔

        从而，在时间轴的不同区间，层层叠叠地叠加上了各个不同的动画对象，不同区间中会有不同的动画对象在发挥作用

        为了得知在某个时刻 ``t`` 有那些动画对象在发挥作用，
        我们肯定不能遍历曾经作用过的所有动画来筛选，这样效率太过低下了

        所以，我们这个物件的动画堆栈，会根据每个动画的起止时刻切分为多个区块，
        我们只需要二分查找出 ``t`` 所处的区块，便可以知道在这个时刻会有哪些动画在发挥作用

        例如：

        如果我们有先后两个动画，``A 0~3s`` 以及 ``B 1~2s``

        一开始为：

        .. code-block::

            starts:  0
            chunks: [ ]

        当我们先加入 ``A`` 后：

        .. code-block::

            starts:  0     |  3
            chunks: [A]    | [ ]

        接着加入 ``B`` 后：

        .. code-block::

            starts:  0     |  1     |  2     |  3
            chunks: [A]    | [A,B]  | [A]    | [ ]

        可以看到，为了加入 ``B``，我们会在 ``1s`` 和 ``2s`` 的位置分别砍一刀

        如果我们再接着加入 ``C 2s~FOREVER``，则：

        .. code-block::

            starts:  0     |  1     |  2     |  3
            chunks: [A]    | [A,B]  | [A,C]  | [C]

        注：由于 :class:`~.Animation` 都会经过 :meth:`~.TimeAligner.align_anim_or_record` 处理，
        所以不必担心由于轻微浮点误差导致产生多余的细切分的问题
        """
        at = anim.t_range.at
        end = anim.t_range.end
        chunk_cnt = len(self._chunks)

        # 检索 [at, end) 要落入的区块范围 [at_idx, end_idx)
        at_idx = None
        end_idx = chunk_cnt if end is FOREVER else None

        idx = chunk_cnt - 1
        # t = _chunk_starts[idx]
        for t in reversed(self._chunk_starts):
            if end_idx is None and t <= end:  # type: ignore
                end_idx = idx
            if end_idx is not None and t <= at:
                at_idx = idx
                break
            idx -= 1

        assert at_idx is not None
        assert end_idx is not None

        # 如果 at 不落于区块边界，则在此处切一刀
        if self._chunk_starts[at_idx] != at:
            at_idx += 1
            self._chunk_starts.insert(at_idx, at)
            self._chunks.insert(at_idx, self._chunks[at_idx - 1].copy())
            end_idx += 1

        # 如果 end 不落于区块边界，则在此处切一刀
        if end_idx != len(self._chunks) and self._chunk_starts[end_idx] != end:
            end_idx += 1
            self._chunk_starts.insert(end_idx, end)  # type: ignore
            self._chunks.insert(end_idx, self._chunks[end_idx - 1].copy())

        # 根据 _cover_previous_anim 的情况来处理
        # - 若 True，则清空所有被该动画所覆盖的所有先前动画
        # - 若 False，则正常 append 到范围内的区块中
        if anim._cover_previous_anims:
            if end_idx - at_idx > 1:
                # 如果覆盖的区块不止一个，则删掉多余的只需要留下一个
                del self._chunk_starts[at_idx + 1 : end_idx]
                del self._chunks[at_idx + 1 : end_idx]
            chunk = self._chunks[at_idx]
            chunk.clear()
            chunk.append(anim)
        else:
            for idx in range(at_idx, end_idx):
                self._chunks[idx].append(anim)

        # 添加了新动画，因此要重置缓存
        if self._cache_time is not None:
            self.clear_cache()

    # endregion

    # region evaluation

    def get_at_left(self, global_t: float) -> list[StackableAnimation]:
        """
        得到 ``global_t`` 所处的区块（即在 ``global_t`` 时发挥作用的动画列表）

        和 :meth:`get` 不同，这个方法将区块区间当作左开右闭处理（即处于边界点时，得到左侧的区块）；
        这个额外的方法在处理某些动画的 ``become_at_end`` 时的计算比较有用

        :param global_t: 全局时刻
        """
        idx = bisect_left(self._chunk_starts, global_t) - 1
        return self._chunks[max(0, idx)]

    def get(self, global_t: float) -> list[StackableAnimation]:
        """
        得到 ``global_t`` 所处的区块（即在 ``global_t`` 时发挥作用的动画列表）

        在区间边界时，遵循区块区间左闭右开的原则（即处于边界点时，得到右侧的区块）
        """
        idx = bisect_right(self._chunk_starts, global_t) - 1
        assert idx >= 0
        return self._chunks[idx]

    def compute(self, global_t: float, readonly: bool, *, get_at_left: bool = False) -> Item:
        """
        得到在 ``global_t`` 时刻下，应用动画作用效果后的物件
        """
        if global_t != self._cache_time:
            self._compute(global_t, readonly, get_at_left)

        assert self._cache_time is not None
        assert self._cache_data is not None
        return self._cache_data if readonly else self._cache_data.store()

    def _compute(self, global_t: float, readonly: bool, get_at_left: bool) -> None:
        # TODO:
        from janim.anims.anim_stack import OldAnimStack

        OldAnimStack.compute(self, global_t, readonly, get_at_left=get_at_left)

    # endregion
