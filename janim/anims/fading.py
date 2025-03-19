
from abc import ABCMeta, abstractmethod

import numpy as np

from janim.anims.updater import DataUpdater, UpdaterParams
from janim.components.glow import Cmpt_Glow
from janim.components.rgbas import Cmpt_Rgbas
from janim.constants import (C_LABEL_ANIM_ABSTRACT, C_LABEL_ANIM_IN,
                             C_LABEL_ANIM_OUT, ORIGIN, OUT)
from janim.items.item import Item
from janim.items.points import Points
from janim.typing import Vect
from janim.utils.paths import PathFunc, get_path_func


class Fade(DataUpdater[Item], metaclass=ABCMeta):
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

        path_arc: float = 0,
        path_arc_axis: Vect = OUT,
        path_func: PathFunc = None,

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
        self.path_func = get_path_func(path_arc, path_arc_axis, path_func)

        if about_point is None and scale != 1.0:
            cmpt = item(Points).points
            box = cmpt.self_box if root_only else cmpt.box
            about_point = box.get(about_edge)
        self.about_point = about_point

    @abstractmethod
    def updater(self, data: Item, p: UpdaterParams) -> None:
        pass    # pragma: no cover


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
            if isinstance(cmpt, Cmpt_Rgbas):
                rgbas = cmpt.get().copy()
                rgbas[:, 3] *= p.alpha
                cmpt.set_rgbas(rgbas)
            elif isinstance(cmpt, Cmpt_Glow):
                cmpt.mix_alpha(0, 1 - p.alpha)

        if self.scale != 1.0:
            data.points.scale(
                (1 - p.alpha) * 1 / self.scale + p.alpha,
                about_point=self.about_point
            )
        if np.any(self.shift != ORIGIN):
            data.points.shift(self.path_func(-self.shift, ORIGIN, p.alpha))


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
        hide_at_end: float = True,
        **kwargs
    ):
        super().__init__(
            item,
            shift,
            scale,
            hide_at_end=hide_at_end,
            **kwargs
        )

    def _time_fixed(self) -> None:
        super()._time_fixed()
        if self.hide_at_end:
            self.timeline.schedule(self.t_range.end, self.item.hide, self.root_only)

    def updater(self, data: Item, p: UpdaterParams) -> None:
        if not isinstance(data, Points):
            return

        for cmpt in data.components.values():
            if isinstance(cmpt, Cmpt_Rgbas):
                rgbas = cmpt.get().copy()
                rgbas[:, 3] *= 1 - p.alpha
                cmpt.set_rgbas(rgbas)
            elif isinstance(cmpt, Cmpt_Glow):
                cmpt.mix_alpha(0, p.alpha)

        if self.scale != 1.0:
            data.points.scale(
                p.alpha * self.scale + (1 - p.alpha),
                about_point=self.about_point
            )
        if np.any(self.shift != ORIGIN):
            data.points.shift(self.path_func(ORIGIN, self.shift, p.alpha))


class FadeInFromPoint(FadeIn):
    def __init__(self, item: Item, point: Vect, **kwargs):
        super().__init__(
            item,
            shift=item(Points).points.box.center - point,
            scale=np.inf,
            **kwargs
        )


class FadeOutToPoint(FadeOut):
    def __init__(self, item: Item, point: Vect, **kwargs):
        super().__init__(
            item,
            shift=point - item(Points).points.box.center,
            scale=0,
            **kwargs
        )
