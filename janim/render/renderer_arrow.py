from __future__ import annotations

from typing import TYPE_CHECKING

from janim.render.base import RenderData
from janim.render.renderer_vitem import VItemPlaneRenderer

if TYPE_CHECKING:
    from janim.items.geometry.arrow import Arrow


class ArrowRenderer(VItemPlaneRenderer):
    shader_path_compatibility = 'render/shaders/vitem/arrow_compatibility'
    shader_path_normal = 'render/shaders/vitem/arrow'

    def init_common(self):
        super().init_common()
        self.u_shrink = self.prog['shrink']
        self.shrink_values = None

    def _update_others(self, item: Arrow, render_data: RenderData, new_attrs: VItemPlaneRenderer.RenderAttrs) -> None:
        if new_attrs.points is not self.attrs.points:
            self.shrink_values = item._get_shrink_values()
        self.u_shrink.value = self.shrink_values


# Arrow 未支持 CurveRenderer
