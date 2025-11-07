from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

import numpy as np

from janim.components.component import CmptInfo
from janim.constants import (DEFAULT_ITEM_TO_ITEM_BUFF, DOWN, LEFT, ORIGIN, PI,
                             RIGHT, UP)
from janim.items.geometry.line import Cmpt_VPoints_LineImpl, Line
from janim.items.points import Points
from janim.items.svg.typst import TypstText
from janim.items.text import Text
from janim.items.vitem import DEFAULT_STROKE_RADIUS, VItem
from janim.typing import Vect
from janim.utils.simple_functions import clip
from janim.utils.space_ops import (angle_of_vector, get_norm, midpoint,
                                   normalize, rotation_between_vectors)

DEFAULT_ARROWTIP_BODY_LENGTH = 0.2
DEFAULT_ARROWTIP_BACK_WIDTH = 0.2


class CenterAnchor(StrEnum):
    '''
    箭头原点所处位置的选项

    图形示意：

    .. code-block:: text

        .-----
        |        -----
        |               -----
        [Back]  [Center]  [Front]
        |               -----
        |        -----
        .-----
    '''
    Back = 'back'
    Center = 'center'
    Front = 'front'


class ArrowTip(VItem):
    '''
    箭头标志

    - ``body_length``: 箭头的宽度
    - ``back_width``: 箭头的长度
    - ``center_anchor``: 原点所处的位置，请参考 :class:`CenterAnchor`
    - ``rotation``: 绕方向轴转动的角度，一般用于 3D 中
    '''

    def __init__(
        self,
        body_length: float = DEFAULT_ARROWTIP_BODY_LENGTH,
        back_width: float = DEFAULT_ARROWTIP_BACK_WIDTH,
        angle: float = 0,
        scale: float = 1,
        *,
        center_anchor: CenterAnchor | Literal['back', 'center', 'front'] = CenterAnchor.Back,
        rotation: float | None = None,
        fill_alpha: float = 1.0,
        stroke_radius: float = DEFAULT_STROKE_RADIUS / 4,
        **kwargs
    ) -> None:
        super().__init__(fill_alpha=fill_alpha, stroke_radius=stroke_radius, **kwargs)
        self.center_anchor = center_anchor

        body_length *= scale
        back_width *= scale
        self.points.set_as_corners([
            body_length * RIGHT,
            back_width / 2 * UP,
            back_width / 2 * DOWN,
            body_length * RIGHT
        ])

        self.points.to_center()
        self.rotate_about_anchor(angle)
        if rotation is not None:
            self.points.rotate(rotation, axis=self.direction)

    def get_center_anchor(self) -> np.ndarray:
        '''
        根据设定的 ``center_anchor`` 得到原点位置，
        请参考 :class:`ArrowTip.CenterAnchor`
        '''
        points = self.points._points.data
        if self.center_anchor == CenterAnchor.Back:
            return points[3]
        if self.center_anchor == CenterAnchor.Center:
            return midpoint(points[0], points[3])
        # if self.center_anchor == CenterAnchor.Front:
        return points[0]

    @property
    def direction(self) -> np.ndarray:
        '''得到箭头的方向（单位向量）'''
        points = self.points._points.data
        return normalize(points[0] - points[3])

    @property
    def body_length(self) -> float:
        '''得到箭头的长度'''
        points = self.points._points.data
        return get_norm(points[0] - points[3])

    @property
    def back_width(self) -> float:
        '''得到箭头的宽度'''
        points = self.points._points.data
        return get_norm(points[4] - points[2])

    def rotate_about_anchor(self, angle: float) -> Self:
        '''相对于原点位置进行旋转'''
        self.points.rotate(angle, about_point=self.get_center_anchor())

    def move_anchor_to(self, pos: np.ndarray) -> Self:
        '''将原点移动到指定位置'''
        self.points.shift(pos - self.get_center_anchor())
        return self


class Cmpt_VPoints_ArrowImpl[ItemT](Cmpt_VPoints_LineImpl[ItemT], impl=True):
    def put_start_and_end_on(self, start: Vect, end: Vect) -> Self:
        super().put_start_and_end_on(start, end)
        if self.bind is not None:
            self.bind.at_item.place_tip()
        return self


class Arrow(Line):
    '''
    带箭头的线段，箭头大小自动

    - ``buff``: 箭头首尾的空余量，默认为 ``0.25``
    - ``max_length_to_tip_length_ratio``: 箭头长度和直线长度最大比例
    '''
    points = CmptInfo(Cmpt_VPoints_ArrowImpl[Self])

    def __init__(
        self,
        start: Vect | Points = LEFT,
        end: Vect | Points = RIGHT,
        *,
        buff: float = 0.25,
        max_length_to_tip_length_ratio: float | None = 0.3,
        tip_kwargs: dict = {},
        **kwargs
    ) -> None:
        if 'center_anchor' not in tip_kwargs:
            tip_kwargs['center_anchor'] = CenterAnchor.Center

        super().__init__(start, end, buff=buff, **kwargs)
        self.max_length_to_tip_length_ratio = max_length_to_tip_length_ratio

        self.init_tips(tip_kwargs)
        self.place_tip()

    def init_tips(self, tip_kwargs: dict) -> None:
        self.tip = self.add_tip(**tip_kwargs)
        self.tip_orig_body_length = self.tip.body_length

    def copy(self, *, root_only=False) -> Self:
        copy_item = super().copy(root_only=root_only)
        if root_only:
            copy_item.tip = None
        else:
            copy_item.tip = copy_item[0]
        return copy_item

    def _place_tip(
        self,
        tip: ArrowTip,
        target: np.ndarray,
        target_direction: np.ndarray
    ) -> None:
        direction = tip.direction

        length = self.tip_orig_body_length

        if self.max_length_to_tip_length_ratio:
            max_length = self.points.arc_length * self.max_length_to_tip_length_ratio
            length = min(length, max_length)

        min_length = self.radius.get()[0] * 2 * self.tip.body_length / self.tip.back_width
        length = max(length, min_length)

        scale_factor = length / tip.body_length

        tip.points.scale(scale_factor)
        if not np.isclose(direction, target_direction).all():
            tip.points.apply_matrix(rotation_between_vectors(direction, target_direction))
        tip.move_anchor_to(target)

    def place_tip(self) -> Self:
        self._place_tip(self.tip, self.points.get_end(), self.points.end_direction)
        return self

    def create_text(
        self,
        text: str,
        place: float = 0.5,
        *,
        use_typst_text: bool = False,
        under: bool = False,
        buff: float = DEFAULT_ITEM_TO_ITEM_BUFF,
        d_place: float = 1e-6,
        **kwargs
    ):
        '''
        创建文字并与箭头对齐

        其中 ``under`` 参数的含义是：

        ``under=False``：

        .. code-block::

                  文字
            ----------------->

        ``under=True``：

        .. code-block::

            ----------------->
                  文字
        '''
        place = clip(place, 0, 1)
        alpha1 = clip(place - d_place, 0, 1)
        alpha2 = clip(place + d_place, 0, 1)

        shift = self.points.pfp(alpha2) - self.points.pfp(alpha1)
        angle = angle_of_vector(shift)
        if shift[0] < 0:
            angle += PI

        about_point = self.points.pfp(place)

        txt = (TypstText if use_typst_text else Text)(text, **kwargs)
        txt.points.next_to(about_point, DOWN if under else UP, buff=buff)
        txt.points.rotate(angle, about_point=about_point)

        return txt


class Vector(Arrow):
    '''
    起点为 ORIGIN 的箭头，终点为 ``direction``

    - ``buff`` 默认设为了 0
    '''
    def __init__(
        self,
        direction: np.ndarray = RIGHT,
        *,
        buff: float = 0,
        tip_kwargs: dict = {},
        **kwargs
    ):
        tip_kwargs.setdefault('center_anchor', CenterAnchor.Front)

        if len(direction) == 2:
            direction = np.hstack([direction, 0])
        super().__init__(ORIGIN, direction, buff=buff, tip_kwargs=tip_kwargs, **kwargs)


class DoubleArrow(Arrow):
    '''
    双向箭头

    参数请参考 :class:`Arrow`
    '''
    def __init__(self, *args, tip_kwargs: dict = {}, **kwargs) -> None:
        super().__init__(*args, tip_kwargs=tip_kwargs, **kwargs)

    def init_tips(self, tip_kwargs: dict) -> None:
        super().init_tips(tip_kwargs)
        self.start_tip = self.add_tip(0, True, **tip_kwargs)

    def copy(self, *, root_only=False) -> Self:
        copy_item = super().copy(root_only=root_only)
        if root_only:
            copy_item.start_tip = None
        else:
            copy_item.start_tip = copy_item[1]
        return copy_item

    def place_tip(self) -> Self:
        super().place_tip()
        self._place_tip(self.start_tip, self.points.get_start(), -self.points.start_direction)
        return self


# TODO: FillArrow
