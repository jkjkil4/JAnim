from bisect import bisect_left, bisect_right
from collections import defaultdict
from contextvars import ContextVar
from typing import Generator

from janim.anims_core.display import Display, DisplayTypes
from janim.anims_core.stackable import ApplyAligner, ApplyParams, StackableAnimation
from janim.anims_core.time import FOREVER, TimeAligner
from janim.items.item import Item


class AnimStack:
    """
    用于记录作用于特定 :class:`~.Item` 上的 :class:`~.StackableAnimation`，形成一个堆栈

    JAnim 动画的核心逻辑：

    后一个动画，会以前一个动画的结果为基础，继续叠加作用

    这就是我们“动画复合”功能的内部逻辑，这个内部结构我们将其称作“动画堆栈”
    """

    get_at_left_ctx: ContextVar[bool] = ContextVar('AnimStack.get_at_left_ctx', default=False)
    """
    用于标记 :meth:`compute` 的 ``get_at_left`` 行为

    .. code-block:: python

        with ContextSetter(AnimStack.get_at_left_ctx, True):
            stack.compute(...)

    使用该 ``ContextVar`` 而非直接向 :meth:`compute` 设置参数，是为了让嵌套调用也能被标记使用 ``get_at_left`` 来处理
    """

    def __init__(self, item: Item, time_aligner: TimeAligner):
        self.item = item
        self.time_aligner = time_aligner

        # 直接调用 clear_cache 即可做到其变量的初始化，具体处理另见 compute 方法
        self.clear_cache()

        # _chunk_starts 和 _chunks 的元素总是一一对应的
        # _chunk_starts 中每个元素，都表示对应的 chunk 的开始时间（以下一个时间点为结束时间）
        # 注：为了方便直接 bisect，没有将他们打包为一个 dataclass，而是将他们各自存储为一个列表
        # 注：关于该算法策略的具体介绍，请参考 append 方法的说明
        self._chunk_starts: list[float] = [0]
        self._chunks: list[list[StackableAnimation]] = [[]]

        # 初始化，给 _chunks 填入一个默认 Display，这里也会初始化 _active_display 和 _latest_display 变量
        #
        # _active_display 变量的含义即为先前记录的物件状态，也可以理解为最后一个与 item 同步状态的 Display 对象
        # Timeline 会在每次前进时间时 detect_change 检查物件，便可使用 _active_display 作为比较基础
        #
        # _latest_display 变量与 _active_display 的区别是，_latest_display 表示最后一个构造的 Display 对象
        # Display 会同时被设置到 _active_display 和 _latest_display 上
        # 而 DelayedDisplay 在构造时就会调用 set_latest_display，但是到了对应的全局时刻才会尝试设置到 _prev_display 上
        self._latest_display: DisplayTypes | None = None
        initial_display = self.display(0)
        # 让初始 Display 的 _order 均为 0
        initial_display._order = 0

    def clear_cache(self) -> None:
        self._cache_key: tuple[float, bool] | None = None
        self._cache_data: Item | None = None

    # region modification

    def display(self, global_t: float) -> Display:
        """
        将物件当前的状态记录到动画堆栈中，将 ``global_t`` 之后都显示为该状态
        """
        anim = Display(self.item.store(), at=global_t, duration=FOREVER)
        anim.finalize()
        self.add(anim, _is_display=True)
        self._active_display: DisplayTypes = anim
        self.set_latest_display(anim)
        return anim

    def set_latest_display(self, anim: DisplayTypes) -> None:
        if self._latest_display is None:
            self._latest_display = anim
        else:
            if anim.t_range.at <= self._latest_display.t_range.at:
                # 当新设置的比原先的 _latest_display 更早，则将原先的 _be_covered 设置为 True
                # 这会使得 DelayedDisplay 的 is_latest_display 标记变为 False
                self._latest_display._be_covered = True

            self._latest_display = anim

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
        return not self._active_display.data_orig.not_changed(self.item)

    def add(self, anim: StackableAnimation, *, _is_display: bool = False) -> None:
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

        注：在添加时，大多数情况如上所示，但是如果动画的 ``_order`` 比较复杂，
        我们需要将后来的动画插入到已有动画堆栈中，而不是直接添加到末尾，这是为了保证每个区块内都是 ``_order`` 升序
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

        for idx in range(at_idx, end_idx):
            chunk = self._chunks[idx]

            # _is_display 为内部参数，表示是否产生于 `display` 方法
            # 用于判断在先前只有单个动画（即 `Display` 动画）时，直接覆盖原来的那个而不是形成堆栈
            if _is_display and len(chunk) == 1:
                if chunk[0]._order <= anim._order:
                    chunk.clear()
                    chunk.append(anim)
            else:
                # 从堆栈末尾向前找，插入 anim 使得 chunk 的 _order 仍然递增
                for idx in range(len(chunk) - 1, -1, -1):
                    if chunk[idx]._order <= anim._order:
                        chunk.insert(idx + 1, anim)
                        break
                else:
                    assert _is_display
                    chunk.insert(0, anim)

        # 添加了新动画，因此要重置缓存
        if self._cache_key is not None:
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

        :param global_t: 全局时刻
        """
        idx = bisect_right(self._chunk_starts, global_t) - 1
        assert idx >= 0
        return self._chunks[idx]

    def compute(self, global_t: float, readonly: bool) -> Item:
        """
        得到在 ``global_t`` 时刻下，应用动画作用效果后的物件

        :param global_t: 全局时刻

        :param readonly: 表示调用方是否会对返回值进行修改

            如果 ``readonly=True`` 则表示不会进行修改，该方法会直接返回缓存本身；
            但是这并没有强制约束性，传入 ``readonly=True`` 时需要遵循不修改返回值的原则，以免影响缓存数据

            如果 ``readonly=False`` 则表示会进行修改，此时会返回缓存的拷贝，从而避免影响缓存数据

            例如：

            -   :meth:`~.Timeline.item_current` 中的调用是 ``readonly=False`` 的，
                因为其返回值最终会被用户使用，我们不能保证用户是否会修改

            -   用于绘制时的调用是 ``readonly=True``，因为绘制时不会对物件数据产生影响

        默认使用 :meth:`get` 获取动画堆栈，可以设置 :py:obj:`get_at_left_ctx` 设定使用 :meth:`get_at_left` 获取动画堆栈，
        具体请参考 :py:obj:`get_at_left_ctx` 的文档

        关于该方法的一些机制细节，请参考 :class:`~.StackableAnimation` 和 :class:`~.ApplyParams` 以及 :class:`~.ApplyAligner` 的介绍

        关于该方法在实现上的一些细节，请参考 ``_compute`` 代码中的注释
        """
        get_at_left = self.get_at_left_ctx.get()

        if (global_t, get_at_left) != self._cache_key:
            self._compute(global_t, get_at_left)

        assert self._cache_key is not None
        assert self._cache_data is not None
        return self._cache_data if readonly else self._cache_data.store()

    def _compute(self, global_t: float, get_at_left: bool) -> None:
        getter = self.get_at_left if get_at_left else self.get
        anims = getter(global_t)
        generator = self._compute_anims(global_t, anims)

        try:
            aligner = next(generator)
        except StopIteration as e:
            # 当 StopIteration 时，说明没有出现 ApplyAligner，直接完成了该动画堆栈的计算
            self._cache_key = (global_t, get_at_left)
            self._cache_data = e.value
        else:
            # 当 generator 被挂起，则出现了 ApplyAligner，需要让 ApplyAligner 的所有目标都“触闸”
            # 具体请参考 `ApplyAligner` 中的介绍

            # 已被挂起的 AnimStack
            # key: AnimStack
            # value: (被挂起的动画堆栈 generator, 由哪个 ApplyAligner 导致的挂起)
            suspended: dict[AnimStack, tuple[Generator, ApplyAligner]] = {
                self: (generator, aligner)
            }

            # 正在等待释放的“闸”
            # key: “闸”的标识值
            # value: 该“闸”包含哪些动画堆栈
            gates: dict[int, list[AnimStack]] = {}

            def setup_gate(identifier: int, stacks: list[AnimStack]) -> None:
                # 执行某个 ApplyAligner 相关联的 stacks，将他们加入到 suspended 中
                # 会跳过已经处于 suspended 中的 stack
                #
                # 什么情况下会有 stack 已经处于 suspended 中？比如下面的例子
                # i1 i2 i3 i4
                # -----------
                #    a1 a2 a3
                # b1 b2 b3
                # 这里有 i1 i2 i3 i4 四个物件
                # - 我们先给 i2 i3 i4 使用了一个 GroupUpdater，创建了 a1 a2 a3 的 ApplyAligner
                # - 接着给 i1 i2 i3 使用了一个 GroupUpdater，创建了 b1 b2 b3 的 ApplyAligner
                # 所以当我们计算 i1 的动画堆栈时
                # - b1 进入 suspended
                # - b2 尝试进入 suspended，但是他前面还有一个 GroupUpdater，所以会把 a1 a2 a3 也拉进 suspended 中
                # - 接着 b3 尝试进入 suspended，由于他前面的 a2 已经在 suspended 了，所以 a2 就不能重复进入
                gates[identifier] = stacks
                for stack in stacks:
                    if stack in suspended:
                        continue
                    getter = stack.get_at_left if get_at_left else stack.get
                    anims = getter(global_t)
                    generator = stack._compute_anims(global_t, anims)

                    # 预期让 generator 吐出一个 ApplyAligner 出来
                    aligner = next(generator)  # 理论上这里不会出现 StopIteration

                    # 加入到 suspended 中，并且如果其“闸”并没有被记录过，则递归收集
                    suspended[stack] = (generator, aligner)
                    if aligner.identifier not in gates:
                        setup_gate(aligner.identifier, aligner.stacks)

            setup_gate(aligner.identifier, aligner.stacks)

            # 只要有在挂起的动画堆栈，就要重复尝试“放闸”
            while suspended:
                # 计数当前挂起的动画堆栈都被什么“闸”给阻挡着
                # 如果某个“闸”的计数达到了其预期的数量，则它可以释放
                counter: defaultdict[int, int] = defaultdict(int)
                for _, (generator, aligner) in suspended.items():
                    identifier = aligner.identifier
                    counter[identifier] += 1
                    if counter[identifier] == len(aligner.stacks):
                        stacks_to_release = aligner.stacks
                        break
                else:
                    assert False  # 断言：一定能找到可放的“闸”

                drop: list[AnimStack] = []  # 记录“放闸”之后，哪些动画堆栈完成了执行

                for stack, (generator, _) in suspended.items():
                    if stack not in stacks_to_release:
                        continue
                    try:
                        aligner = next(generator)
                        # “放闸”后，该动画堆栈没有结束
                        suspended[stack] = (generator, aligner)
                        if aligner.identifier not in gates:
                            setup_gate(aligner.identifier, aligner.stacks)
                    except StopIteration as e:
                        # “放闸”后，该动画堆栈结束
                        drop.append(stack)
                        stack._cache_key = (global_t, get_at_left)
                        stack._cache_data = e.value

                # 将完成执行的动画堆栈移出 suspended
                suspended = {
                    stack: tup
                    for stack, tup in suspended.items()
                    if stack not in drop  #
                }

    def _compute_anims(
        self, global_t: float, anims: list[StackableAnimation]
    ) -> Generator[ApplyAligner, None, None]:
        assert anims  # 断言 anims 一定非空

        # 当 anims 中只有一个动画时，一定是 Display，直接返回其 data_orig
        if len(anims) == 1:
            return anims[0].data_orig  # type: ignore

        # 这里设置 None 是有意的，它一上来就会被 Display 设置初始值，所以不会造成问题
        params = ApplyParams(None, global_t, 0, anims)  # type: ignore

        for i, anim in enumerate(anims):
            params.index = i
            if i != 0 and isinstance(anim, ApplyAligner):
                anim.pre_apply(params)
                yield anim
            anim.apply(params)

        return params.data  # type: ignore

    # endregion
