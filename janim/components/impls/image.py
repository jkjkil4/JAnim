from __future__ import annotations

from typing import Self

from PIL import Image

from janim.components.core.attrs import ComponentAttrs
from janim.components.core.component import Component


class Cmpt_Image[ItemT](Component[ItemT]):
    """
    图像组件，包含一个 PIL 图像以及 ``min_mag_filter``
    """

    _attrs = ComponentAttrs()
    img = _attrs.direct_object(Image.Image, nullable=True)
    min_mag_filter = _attrs.direct_object(tuple[int, int], nullable=True)

    def set(
        self, img: Image.Image | None = None, min_mag_filter: tuple[int, int] | None = None
    ) -> Self:
        """
        设置 PIL 图像
        """
        if img is not None:
            self.img = img
        if min_mag_filter is not None:
            self.min_mag_filter = min_mag_filter
        return self

    def get(self) -> Image.Image:
        assert self.img is not None
        return self.img

    def get_filter(self) -> tuple[int, int]:
        assert self.min_mag_filter is not None
        return self.min_mag_filter
