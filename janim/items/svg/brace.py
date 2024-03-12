
import math
import os
from typing import Self

import numpy as np

from janim.anims.timeline import Timeline
from janim.components.component import CmptInfo
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import DEFAULT_ITEM_TO_ITEM_BUFF, DOWN, PI, SMALL_BUFF
from janim.items.item import Item
from janim.items.points import Points
from janim.items.svg.svg_item import SVGItem
from janim.items.svg.typst import Typst
from janim.items.text.text import Text
from janim.items.vitem import VItem
from janim.typing import Vect
from janim.utils.file_ops import get_janim_dir
from janim.utils.space_ops import normalize, rotation_about_z


class Cmpt_VPoints_BraceImpl(Cmpt_VPoints, impl=True):
    # 复制时，``length`` 随 ``copy.copy(self)`` 而复制，因此不用重写 ``copy`` 方法
    def match(self, item: Points | None, direction: Vect, buff: float = SMALL_BUFF) -> Self:
        self.set(get_brace_orig_points())

        if item is None:
            self.length = self.box.width
            return

        angle = math.atan2(direction[1], direction[0]) + PI / 2
        rot = np.array(rotation_about_z(-angle))
        rot_points = np.dot(item.points.get(), rot.T)   # dot(points, rot.T) == dot(rot, points.T).T

        box = self.BoundingBox(rot_points)

        self.set_width(box.width, stretch=box.width > self.box.width)
        self.move_to(box.bottom + DOWN * (buff + self.box.height / 2))
        self.apply_matrix(rot.T)     # rot.T == rot.I

        self.length = box.width

        return self

    @property
    def tip_point(self) -> np.ndarray:
        return self._points._data[get_brace_tip_point_index()].copy()

    @property
    def direction(self) -> np.ndarray:
        return normalize(self.tip_point - self.box.center)

    def put_at_tip(
        self,
        item_or_data: Points | Item.Data[Points],
        use_next_to: bool = True,
        buff: float = DEFAULT_ITEM_TO_ITEM_BUFF,
        **kwargs
    ) -> Self:
        if isinstance(item_or_data, Points):
            cmpt = item_or_data.points
        else:
            cmpt = item_or_data.cmpt.points

        if use_next_to:
            cmpt.next_to(
                self.tip_point,
                np.round(self.direction),
                buff=buff,
                **kwargs
            )
        else:
            cmpt.move_to(self.tip_point)
            shift_distance = cmpt.box.width * 0.5 + buff
            cmpt.shift(self.direction * shift_distance)

    def create_text(self, text: str, buff: float = SMALL_BUFF, use_next_to: bool = True, **kwargs) -> Text:
        txt = Text(text, **kwargs)
        self.put_at_tip(txt, use_next_to=use_next_to, buff=buff)
        return txt

    def create_typst(self, typst: str, buff: float = SMALL_BUFF, use_next_to: bool = True, **kwargs) -> Typst:
        typ = Typst(typst, **kwargs)
        self.put_at_tip(typ, use_next_to=use_next_to, buff=buff)
        return typ


class Brace(VItem):
    points = CmptInfo(Cmpt_VPoints_BraceImpl)

    def __init__(
        self,
        item: Points | None = None,
        direction: np.ndarray = DOWN,
        buff: float = SMALL_BUFF,
        stroke_alpha: float = 0,
        fill_alpha: float = 1,
        **kwargs
    ):
        super().__init__(stroke_alpha=stroke_alpha, fill_alpha=fill_alpha, **kwargs)
        self.points.match(item, direction, buff)


brace_orig_points: np.ndarray | None = None
brace_tip_point_index: int | None = None


def get_brace_orig_points() -> np.ndarray:
    global brace_orig_points
    if brace_orig_points is not None:
        return brace_orig_points

    with Timeline.CtxBlocker():
        svg = SVGItem(os.path.join(get_janim_dir(), 'items', 'svg', 'brace.svg'))
    points = svg[0].points.get()
    points -= (points.min(axis=0) + points.max(axis=0)) * 0.5
    brace_orig_points = points

    return brace_orig_points


def get_brace_tip_point_index() -> np.ndarray:
    global brace_tip_point_index
    if brace_tip_point_index is not None:
        return brace_tip_point_index

    points = get_brace_orig_points()
    brace_tip_point_index = points[:, 1].argmin()

    return brace_tip_point_index
