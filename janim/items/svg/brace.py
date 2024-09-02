
import math
import os
from typing import Self

import numpy as np

from janim.components.component import CmptInfo
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import DEFAULT_ITEM_TO_ITEM_BUFF, DOWN, PI, SMALL_BUFF
from janim.items.points import Points
from janim.items.svg.svg_item import SVGItem
from janim.items.svg.typst import Typst
from janim.items.text.text import Text
from janim.items.vitem import VItem
from janim.typing import Vect
from janim.utils.file_ops import get_janim_dir
from janim.utils.space_ops import normalize, rotation_about_z


class Cmpt_VPoints_BraceImpl[ItemT](Cmpt_VPoints[ItemT], impl=True):
    '''
    在 :class:`Brace` 中对 :class:`Cmpt_VPoints` 的进一步实现
    '''
    # 复制时，``brace_length`` 随 ``copy.copy(self)`` 而复制，因此不用重写 ``copy`` 方法
    def match(
        self,
        item: Points | None,
        direction: Vect | None = None,
        buff: float = SMALL_BUFF,
        root_only: bool = False
    ) -> Self:
        '''
        将花括号进行伸缩，使得与 ``item`` 在 ``direction`` 方向的宽度匹配
        '''
        if direction is None:
            direction = self.direction if self.has() else DOWN

        self.set(get_brace_orig_points())

        angle = math.atan2(direction[1], direction[0]) + PI / 2
        rot = np.array(rotation_about_z(-angle))

        if item is None:
            self.brace_length = self.box.width
        else:
            cmpt = item.points

            # points @ rot.T == (rot @ points.T).T
            rot_points = (cmpt.get() if root_only else cmpt.get_all()) @ rot.T

            box = self.BoundingBox(rot_points)
            self.brace_length = box.width

            self.set_width(box.width, stretch=box.width > self.box.width)
            self.move_to(box.bottom + DOWN * (buff + self.box.height / 2))

        self.apply_matrix(rot.T)     # rot.T == rot.I

        return self

    @property
    def tip_point(self) -> np.ndarray:
        '''得到花括号中间凸出处的坐标'''
        return self._points.data[get_brace_tip_point_index()]

    @property
    def brace_left(self) -> np.ndarray:
        '''得到括号指向方向左边的尖端处的坐标'''
        return self._points.data[get_brace_left_index()]

    @property
    def brace_right(self) -> np.ndarray:
        '''得到括号指向方向右边的尖端处的坐标'''
        return self._points.data[get_brace_right_index()]

    @property
    def direction(self) -> np.ndarray:
        '''得到括号指向的方向'''
        return normalize(self.tip_point - self.box.center)

    def put_at_tip(
        self,
        item: Points,
        use_next_to: bool = True,
        buff: float = DEFAULT_ITEM_TO_ITEM_BUFF,
        **kwargs
    ) -> Self:
        '''
        将物件放置在花括号中间的凸出处
        '''
        cmpt = item.points

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
        '''创建一个位于花括号中间凸出处的文字'''
        txt = Text(text, **kwargs)
        self.put_at_tip(txt, use_next_to=use_next_to, buff=buff)
        return txt

    def create_typst(self, typst: str, buff: float = SMALL_BUFF, use_next_to: bool = True, **kwargs) -> Typst:
        '''创建一个位于花括号中间凸出处的 Typst 公式'''
        typ = Typst(typst, **kwargs)
        self.put_at_tip(typ, use_next_to=use_next_to, buff=buff)
        return typ


class Brace(VItem):
    '''
    花括号物件

    会匹配物件在 ``direction`` 方向的宽度
    '''
    points = CmptInfo(Cmpt_VPoints_BraceImpl[Self])

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
brace_left_index: int | None = None
brace_right_index: int | None = None


def get_brace_orig_points() -> np.ndarray:
    global brace_orig_points
    if brace_orig_points is not None:
        return brace_orig_points

    svg = SVGItem(os.path.join(get_janim_dir(), 'items', 'svg', 'brace.svg'))
    points = svg[0].points.get()
    center = (points.min(axis=0) + points.max(axis=0)) * 0.5

    brace_orig_points = points - center
    brace_orig_points.setflags(write=False)
    return brace_orig_points


def get_brace_tip_point_index() -> int:
    global brace_tip_point_index
    if brace_tip_point_index is not None:
        return brace_tip_point_index

    points = get_brace_orig_points()
    brace_tip_point_index = points[:, 1].argmin()

    return brace_tip_point_index


def get_brace_left_index() -> int:
    global brace_left_index
    if brace_left_index is not None:
        return brace_left_index

    points = get_brace_orig_points()
    brace_left_index = points[:, 0].argmin()

    return brace_left_index


def get_brace_right_index() -> int:
    global brace_right_index
    if brace_right_index is not None:
        return brace_right_index

    points = get_brace_orig_points()
    brace_right_index = points[:, 0].argmax()

    return brace_right_index
