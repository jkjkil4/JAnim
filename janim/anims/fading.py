
from abc import ABCMeta, abstractmethod

import numpy as np

from janim.anims.updater import DataUpdater, UpdaterParams
from janim.components.rgbas import Cmpt_Rgbas
from janim.constants import (C_LABEL_ANIM_ABSTRACT, C_LABEL_ANIM_IN,
                             C_LABEL_ANIM_OUT, ORIGIN)
from janim.items.item import Item
from janim.items.points import Points
from janim.typing import Vect


class Fade(DataUpdater, metaclass=ABCMeta):
    '''
    :class:`FadeIn` 和 :class:`FadeOut` 的基类
    '''
    label_color = C_LABEL_ANIM_ABSTRACT

    def __init__(
        self,
        item: Item,
        shift: Vect = ORIGIN,
        scale: float = 1.0,
        *,
        about_point: Vect | None = None,
        about_edge: Vect = ORIGIN,
        become_at_end: bool = False,
        root_only: bool = False,
        **kwargs
    ):
        super().__init__(
            item,
            self.updater,
            become_at_end=become_at_end,
            root_only=root_only,
            **kwargs
        )
        self.shift = np.array(shift)
        self.scale = scale

        if about_point is None and scale != 1.0:
            cmpt = item(Points).points
            box = cmpt.self_box if root_only else cmpt.box
            about_point = box.get(about_edge)
        self.about_point = about_point

    @abstractmethod
    def updater(self, data: Item, p: UpdaterParams) -> None:
        pass


class FadeIn(Fade):
    '''
    淡入

    - 可以使用 ``shift`` 指定淡入位移
    - 可以使用 ``scale`` 指定淡入缩放
    '''
    label_color = C_LABEL_ANIM_IN

    def updater(self, data: Item, p: UpdaterParams) -> None:
        if not isinstance(data, Points):
            return

        for cmpt in data.components.values():
            if not isinstance(cmpt, Cmpt_Rgbas):
                continue
            rgbas = cmpt.get().copy()
            rgbas[:, 3] *= p.alpha
            cmpt.set_rgbas(rgbas)

        if np.any(self.shift != ORIGIN):
            data.points.shift((1 - p.alpha) * -self.shift)
        if self.scale != 1.0:
            data.points.scale(
                (1 - p.alpha) * 1 / self.scale + p.alpha,
                about_point=self.about_point
            )


class FadeOut(Fade):
    '''
    淡出

    - 可以使用 ``shift`` 指定淡出位移
    - 可以使用 ``scale`` 指定淡出缩放
    '''
    label_color = C_LABEL_ANIM_OUT

    def __init__(
        self,
        item: Item,
        shift: Vect = ORIGIN,
        scale: float = 1.0,
        show_at_end: float = False,
        **kwargs
    ):
        super().__init__(
            item,
            shift,
            scale,
            show_at_end=show_at_end,
            **kwargs
        )

    def updater(self, data: Item, p: UpdaterParams) -> None:
        if not isinstance(data, Points):
            return

        for cmpt in data.components.values():
            if not isinstance(cmpt, Cmpt_Rgbas):
                continue
            rgbas = cmpt.get().copy()
            rgbas[:, 3] *= 1 - p.alpha
            cmpt.set_rgbas(rgbas)

        if np.any(self.shift != ORIGIN):
            data.points.shift(p.alpha * self.shift)
        if self.scale != 1.0:
            data.points.scale(
                p.alpha * self.scale + (1 - p.alpha),
                about_point=self.about_point
            )
