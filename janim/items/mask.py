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


class Mask(Points):
    """
    蒙版物件，用于遮罩受影响的物件

    通过传入一个 :class:`~.VItem` 作为形状，将受影响物件中位于形状外部的部分隐藏

    支持透明度 (`mask_alpha`)、羽化 (`feather`)、反转 (`invert`)

    例：

    .. code-block:: python

        circle = Circle(fill_alpha=1.0, color=BLUE)
        text = Text("Hello", color=GREEN)

        circle.show()
        text.show()

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
        添加受蒙版影响的物件
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
        移除受蒙版影响的物件
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

    def _mark_render_disabled(self, additionals: list[Timeline.AdditionalRenderCallsCallback]):
        for appr in self._affected_apprs:
            appr.render_disabled = True

        self._additional_lists = []

        for rcc in additionals:
            if rcc.related_items is not None and all(item in self._affected_items for item in rcc.related_items):
                rcc.render_disabled = True
                self._additional_lists.append(rcc.func())

    @classmethod
    def align_for_interpolate(cls, item1: Mask, item2: Mask) -> AlignedData[Self]:
        aligned = super().align_for_interpolate(item1, item2)

        # 合并两个 Mask 的受影响物件列表
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
