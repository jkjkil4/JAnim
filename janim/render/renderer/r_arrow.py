from __future__ import annotations

from typing import TYPE_CHECKING

from janim_backend import gl

from janim.render.base import RenderData
from janim.render.renderer.r_vitem import VItemPlaneRenderer

if TYPE_CHECKING:
    from janim.items.geometry.arrow import Arrow


class ArrowRenderer(VItemPlaneRenderer):
    shader_path_compatibility = 'render/shaders/vitem/vitem_plane/_arrow_compa_'
    shader_path_normal = 'render/shaders/vitem/vitem_plane/_arrow_normal_'

    def init_common(self):
        super().init_common()
        self.u_shrink = self.uniform(self.prog, 'shrink', gl.GL_FLOAT_VEC2)
        self.shrink_values = None

    def _update_others(
        self, item: Arrow, render_data: RenderData, new_attrs: VItemPlaneRenderer.RenderAttrs
    ) -> None:
        if new_attrs.points is not self.attrs.points:
            self.shrink_values = item._get_shrink_values()
        self.u_shrink.write_vec2(*self.shrink_values)  # type: ignore


# Arrow 未支持 CurveRenderer
