from __future__ import annotations

import itertools as it
from typing import TYPE_CHECKING, Self

from janim.anims.timeline import Timeline
from janim.components.component import CmptInfo
from janim.components.rgbas import Cmpt_Rgbas
from janim.components.simple import Cmpt_Float, Cmpt_List
from janim.components.vpoints import Cmpt_VPoints
from janim.items.item import Item
from janim.items.points import Points
from janim.render.renderer_mask import MaskRenderer
from janim.utils.data import AlignedData

if TYPE_CHECKING:
    from janim.anims.timeline import Timeline
    from janim.items.vitem import VItem


class ShapeMask(Points):
    """
    用 ``shape`` 的轮廓做一个蒙版。

    被加入到 ``affected`` 里的物件，只会显示形状内部的部分。

    - ``mask_alpha``: 蒙版整体透明度，范围 ``0.0`` ~ ``1.0``
    - ``feather``: 边缘羽化，值越大越模糊
    - ``invert``: 反转蒙版，``0.0`` 为正常，``1.0`` 为完全反转

    创建后也可以用 :meth:`affect` / :meth:`disaffect` 增删受影响的物件

    .. code-block:: python

        text = Text("Hello")
        mask = Mask(Circle(radius=2), affected=[text], feather=0.2)
        mask.show()
    """
    renderer_cls = MaskRenderer

    points = CmptInfo(Cmpt_VPoints[Self])
    fill = CmptInfo(Cmpt_Rgbas[Self])
    mask_alpha = CmptInfo(Cmpt_Float[Self], 1.0)
    feather = CmptInfo(Cmpt_Float[Self], 0.0)
    invert = CmptInfo(Cmpt_Float[Self], 0.0)

    _affected_items = CmptInfo(Cmpt_List[Self, Item])
    _affected_apprs = CmptInfo(Cmpt_List[Self, "Timeline.ItemAppearance"])

    def __init__(
        self,
        shape: VItem,
        *,
        affected: list[Item] | None = None,
        alpha: float = 1.0,
        feather: float = 0.0,
        invert: bool = False,
        root_only: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)

        subpaths = []
        for item in shape.walk_self_and_descendants():
            if hasattr(item, 'points') and hasattr(item.points, 'get_subpaths') and item.points.has():
                subpaths.extend(item.points.get_subpaths())

        for subpath in subpaths:
            self.points.add_subpath(subpath)

        self.fill.set([1.0, 1.0, 1.0], 1.0, root_only=True)
        self.mask_alpha.set(alpha)
        self.feather.set(feather)
        self.invert.set(1.0 if invert else 0.0)

        if affected is not None:
            self.affect(*affected, root_only=root_only)

    def affect(self, *items: Item, root_only: bool = False) -> Self:
        """
        把物件加入这个蒙版的影响范围
        """
        apply_items = [
            sub
            for item in items
            for sub in item.walk_self_and_descendants(root_only)
            if sub not in self._affected_items
        ]
        self._affected_items.extend(apply_items)
        self._affected_apprs.extend(
            self.timeline.item_appearances[item]
            for item in apply_items
        )
        return self

    def disaffect(self, *items: Item, root_only: bool = False) -> Self:
        """
        把物件从这个蒙版的影响范围里移除
        """
        for item in items:
            for sub in item.walk_self_and_descendants(root_only):
                try:
                    idx = self._affected_items.index(sub)
                    self._affected_items.pop(idx)
                    self._affected_apprs.pop(idx)
                except ValueError:
                    pass
        return self

    class _StaticStack:
        def __init__(self, data: ShapeMask):
            self._data = data

        def compute(self, t: float, readonly: bool) -> ShapeMask:
            return self._data

    class _NestedRenderAppr:
        """
        给已经挂在别的遮罩下面的目标补一层中转节点。

        这些目标这一帧仍然要走当前遮罩的渲染逻辑，但不能直接改
        ``render_parent``，不然原来的嵌套顺序会乱。
        """
        def __init__(self, data: ShapeMask, render_func):
            self.current_data = data
            self.stack = ShapeMask._StaticStack(data)
            self._render_func = render_func
            self.render_disabled = False
            self.render_parent = None

        def is_visible_at(self, t: float) -> bool:
            return True

        def render(self, data: ShapeMask) -> None:
            self._render_func(data)

    @classmethod
    def _find_nested_host(cls, parent_appr, target_appr):
        parent_data = getattr(parent_appr, 'current_data', None)
        if parent_data is None:
            return None

        parent_targets = getattr(parent_data, '_render_targets', ())
        for child_appr in parent_targets:
            if child_appr is target_appr:
                return parent_appr

            nested_host = cls._find_nested_host(child_appr, target_appr)
            if nested_host is not None:
                return nested_host

        # 不能只看 render_parent。这个字段这一帧里可能还没更新，
        # 也可能已经被别处改过。这里再查一遍 _affected_apprs，
        # 确认目标现在是不是还归这个父遮罩管。
        affected_apprs = getattr(parent_data, '_affected_apprs', None)
        if affected_apprs is not None and target_appr in affected_apprs:
            return parent_appr

        return None

    @classmethod
    def _find_existing_chain_parent(cls, appr):
        # 只复用现在还能确认有效的父节点。
        # 这样共享目标不会挂回已经失效的旧遮罩。
        parent_appr = appr.render_parent
        while parent_appr is not None:
            nested_host = cls._find_nested_host(parent_appr, appr)
            if nested_host is not None:
                return nested_host
            parent_appr = getattr(parent_appr, 'render_parent', None)

        return None

    def _mark_render_disabled(self, self_appr, additionals: list[Timeline.AdditionalRenderCallsCallback]):
        # 这一帧由当前遮罩直接渲染的目标。
        self._render_targets = []

        nested_by_affected = {}
        affected_pairs = list(zip(self._affected_items, self._affected_apprs))

        if self_appr is not None:
            shared_by_parent = {}

            # 共享目标如果已经在别的遮罩链里，就继续放在原链上。
            # 否则当前遮罩一接手，就会把嵌套顺序弄乱。
            for item, appr in affected_pairs:
                parent_appr = self._find_existing_chain_parent(appr)
                if parent_appr is None:
                    continue

                shared_by_parent.setdefault(parent_appr, []).append((item, appr))

            for parent_appr, shared_pairs in shared_by_parent.items():
                shared_items = [item for item, _ in shared_pairs]
                shared_apprs = [appr for _, appr in shared_pairs]

                # 给每个父遮罩补一层中转节点，只处理这组共享目标。
                # 这样能继续复用当前遮罩的渲染逻辑，又不改它们原来的父链。
                nested_data = self.copy(root_only=True)
                nested_data._render_targets = shared_apprs.copy()
                nested_data._affected_items.clear()
                nested_data._affected_items.extend(shared_items)
                nested_data._affected_apprs.clear()
                nested_data._affected_apprs.extend(shared_apprs)
                nested_data._additional_lists = []

                nested_appr = self._NestedRenderAppr(nested_data, self_appr.render)
                nested_appr.render_parent = parent_appr

                for appr in shared_apprs:
                    nested_by_affected[appr] = nested_appr

                parent_data = parent_appr.current_data
                parent_targets = list(getattr(parent_data, '_render_targets', ()))
                shared_set = set(shared_apprs)
                new_parent_targets = []
                inserted = False
                for target in parent_targets:
                    if target in shared_set:
                        if not inserted:
                            # 尽量插回原来的位置，别改父遮罩里现有的渲染顺序。
                            # 如果这一帧还没收集到这些目标，就走下面的追加分支。
                            new_parent_targets.append(nested_appr)
                            inserted = True
                    else:
                        new_parent_targets.append(target)
                if not inserted:
                    new_parent_targets.append(nested_appr)
                parent_data._render_targets = new_parent_targets

        for _, appr in affected_pairs:
            nested_appr = nested_by_affected.get(appr)
            if nested_appr is not None:
                appr.render_parent = nested_appr
            else:
                if self_appr is not None:
                    appr.render_parent = self_appr
                self._render_targets.append(appr)
            appr.render_disabled = True

        if self_appr is not None and not self._render_targets and nested_by_affected:
            # 当前遮罩已经没有自己要画的目标时，就不要再单独渲染它。
            # 如果这些中转节点都挂在同一个父节点下，再把当前遮罩接回去，
            # 免得外层链断掉。
            parent_candidates = {nested_appr.render_parent for nested_appr in nested_by_affected.values()}
            self_appr.render_disabled = True
            if len(parent_candidates) == 1:
                self_appr.render_parent = next(iter(parent_candidates))

        self._additional_lists = []

        for rcc in additionals:
            if rcc.related_items is not None and all(item in self._affected_items for item in rcc.related_items):
                rcc.render_disabled = True
                self._additional_lists.append(rcc.func())

    @classmethod
    def align_for_interpolate(cls, item1: ShapeMask, item2: ShapeMask) -> AlignedData[Self]:
        aligned = super().align_for_interpolate(item1, item2)

        # 按对象身份合并 affected，保证同一个共享对象前后都还对应同一个 appearance。
        # 否则插值后会把它当成新目标，原来的父遮罩链就接不上了。
        merged_items = list(dict.fromkeys(
            it.chain(item1._affected_items, item2._affected_items)
        ))
        item1_map = {id(item1._affected_items[i]): item1._affected_apprs[i]
                     for i in range(len(item1._affected_items))}
        item2_map = {id(item2._affected_items[i]): item2._affected_apprs[i]
                     for i in range(len(item2._affected_items))}

        merged_apprs = []
        for item in merged_items:
            item_id = id(item)
            if item_id in item1_map:
                merged_apprs.append(item1_map[item_id])
            elif item_id in item2_map:
                merged_apprs.append(item2_map[item_id])

        for data in (aligned.data1, aligned.data2, aligned.union):
            data._affected_items.clear()
            data._affected_items.extend(merged_items)
            data._affected_apprs.clear()
            data._affected_apprs.extend(merged_apprs)

        return aligned
