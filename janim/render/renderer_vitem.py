from __future__ import annotations

from typing import TYPE_CHECKING

from janim.render.base import Renderer
from janim.render.renderer_vitem_plane import VItemPlaneRenderer
from janim.render.renderer_vitem_curve import VItemCurveRenderer


if TYPE_CHECKING:
    from janim.items.vitem import VItem


class VItemRenderer(Renderer):
    plane_renderer_cls = VItemPlaneRenderer
    curve_renderer_cls = VItemCurveRenderer

    def __init__(self):
        self.plane_renderer = self.plane_renderer_cls()
        self.curve_renderer = self.curve_renderer_cls()

        self.prev_fill = None

    def render(self, item: VItem) -> None:
        if item._depth_test:
            new_fill = item.fill._rgbas._data
            if new_fill is not self.prev_fill:
                self.fill_transparent = item.fill.is_transparent()
                self.prev_fill = new_fill

            if self.fill_transparent:
                self.curve_renderer.render(item)
            else:
                self.plane_renderer.render(item)

        else:
            self.plane_renderer.render(item)
