
import math
import os
from typing import Self

import numpy as np

from janim.components.component import CmptInfo
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import (DEFAULT_ITEM_TO_ITEM_BUFF, DOWN, LEFT, PI,
                             SMALL_BUFF)
from janim.items.points import Points
from janim.items.svg.typst import TypstMath
from janim.items.text import Text
from janim.items.vitem import VItem
from janim.typing import Vect
from janim.utils.bezier import PathBuilder
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

        angle = math.atan2(direction[1], direction[0])
        rot = np.array(rotation_about_z(-angle + PI))

        if item is None:
            self.brace_length = get_brace_default_length()
            self.set(get_brace_unique_points())
        else:
            cmpt = item.points

            # points @ rot.T == (rot @ points.T).T
            rot_points = (cmpt.get() if root_only else cmpt.get_all()) @ rot.T

            box = self.BoundingBox(rot_points)
            self.brace_length = box.height

            delta = self.brace_length - get_brace_default_length()
            if delta <= 0:
                self.set(get_brace_unique_points())
                self.set_height(self.brace_length)
                min_thickness = get_brace_default_thickness() / 2
                if self.box.width < min_thickness:
                    self.set_width(min_thickness, stretch=True)
            else:
                offset = delta / 2
                path1, path2, path3, path4 = get_brace_paths()
                path1 = path1 + [0, -offset, 0]
                path3 = path3 + [0, offset, 0]
                builder = PathBuilder(points=path1)
                for path in (path2, path3, path4):
                    builder.line_to(path[0])
                    builder.append(path[1:])
                builder.close_path()
                self.set(builder.get())

            self.move_to(box.left + LEFT * (buff + self.box.width / 2))

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
        return normalize(self.tip_point - (self.brace_left + self.brace_right) / 2)

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

    def create_typst(self, typst: str, buff: float = SMALL_BUFF, use_next_to: bool = True, **kwargs) -> TypstMath:
        '''创建一个位于花括号中间凸出处的 Typst 公式'''
        typ = TypstMath(typst, **kwargs)
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
        root_only: bool = False,
        stroke_alpha: float = 0,
        fill_alpha: float = 1,
        **kwargs
    ):
        super().__init__(stroke_alpha=stroke_alpha, fill_alpha=fill_alpha, **kwargs)
        self.points.match(item, direction, buff, root_only)


_brace_unique_points: np.ndarray | None = None
_brace_default_length: float | None = None
_brace_default_thickness: float | None = None
_brace_tip_point_index: int | None = None
_brace_left_index: int | None = None
_brace_right_index: int | None = None

_brace_paths: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None


def get_brace_unique_points() -> np.ndarray:
    global _brace_unique_points
    if _brace_unique_points is None:
        _brace_unique_points = np.load(os.path.join(get_janim_dir(), 'items', 'svg', 'brace_unique.npy'))
        _brace_unique_points.setflags(write=False)
    return _brace_unique_points


def get_brace_default_length() -> float:
    global _brace_default_length
    if _brace_default_length is None:
        points = get_brace_unique_points()
        _brace_default_length = points[:, 1].max() - points[:, 1].min()
    return _brace_default_length


def get_brace_default_thickness() -> float:
    global _brace_default_thickness
    if _brace_default_thickness is None:
        points = get_brace_unique_points()
        _brace_default_thickness = points[:, 0].max() - points[:, 0].min()
    return _brace_default_thickness


def get_brace_tip_point_index() -> int:
    global _brace_tip_point_index
    if _brace_tip_point_index is None:
        _brace_tip_point_index = get_brace_unique_points()[:, 0].argmin()
    return _brace_tip_point_index


def get_brace_left_index() -> int:      # 注：“left”表示“括号指向方向的左侧”，在原顶点数据中实为顶部
    global _brace_left_index
    if _brace_left_index is None:
        _brace_left_index = get_brace_unique_points()[:, 1].argmax()
    return _brace_left_index


def get_brace_right_index() -> int:     # 注：“right”表示“括号指向方向的右侧”，在原顶点数据中实为底部
    global _brace_right_index
    if _brace_right_index is None:
        _brace_right_index = get_brace_unique_points()[:, 1].argmin()
    return _brace_right_index


def get_brace_paths() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    global _brace_paths

    if _brace_paths is None:
        def get_path(i: int):
            path: np.ndarray = np.load(os.path.join(get_janim_dir(), 'items', 'svg', f'brace_path{i}.npy'))
            path.setflags(write=False)
            return path

        _brace_paths = tuple(get_path(i) for i in range(1, 5))

    return _brace_paths
