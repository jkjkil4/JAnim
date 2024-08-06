from __future__ import annotations

from typing import Self

from PIL import Image

from janim.components.component import Component


class Cmpt_Image[ItemT](Component[ItemT]):
    '''
    图像组件，包含一个 PIL 图像以及 ``min_mag_filter``
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.img = None
        self.min_mag_filter = None

    def copy(self) -> Self:
        # self.img 没必要 copy
        # self.min_mag_filter 已通过父方法 copy.copy 复制
        return super().copy()

    def become(self, other: Cmpt_Image) -> Self:
        self.set(other.img, other.min_mag_filter)
        return self

    def not_changed(self, other: Cmpt_Image) -> bool:
        return id(self.img) == id(other.img) and self.min_mag_filter == other.min_mag_filter

    def set(self, img: Image.Image | None = None, min_mag_filter: int | None = None) -> Self:
        '''
        设置 PIL 图像
        '''
        if img is not None:
            self.img = img
        if min_mag_filter is not None:
            self.min_mag_filter = min_mag_filter
        return self

    def get(self) -> Image.Image:
        return self.img

    def get_filter(self) -> int:
        return self.min_mag_filter
