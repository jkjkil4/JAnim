from __future__ import annotations

import math
from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np

from janim.components.points import Cmpt_Points
from janim.render.base import Renderer
from janim.render.framebuffer import FrameBuffer
from janim.render.program import get_program_from_file_prefix
from janim.render.renderer.r_vitem import VItemRenderer
from janim.utils.config import Config
from janim.utils.font.database import ORIG_FONT_SIZE

if TYPE_CHECKING:
    from janim.items.text import TextChar

_SIZE_UNIT = 12


class TextCharRenderer(VItemRenderer):
    def render(self, item: TextChar) -> None:  # type: ignore
        if item._pixel_render_attrs is None:
            super().render(item)
        else:
            item._pixel_render_attrs.render(item)


class PixelRenderInfo:
    """
    存储 ``PixelText`` 绘制模式需要用到的信息，并在 :class:`TextCharRenderer` 中被调用以渲染

    :param unicode: 字符的 unicode
    :param standard_outline: 该字符所对应的标准 outline，即 :meth:`~.Font.get_glyph_data` 的返回值
    :param font_size: 当前指定的字号
    """

    def __init__(self, unicode: str, standard_outline: np.ndarray, font_size: float):
        self.unicode = unicode
        self.standard_outline = standard_outline
        self.font_size = font_size

        self._initialized: bool = False

    def init(self) -> None:
        self.ctx = Renderer.data_ctx.get().ctx
        self.texture = CharTexture.get(
            self.ctx, self.unicode, self.standard_outline, self.font_size
        )

    def render(self, item: TextChar) -> None:
        if not self._initialized:
            self.init()
            self._initialized = True

        self.texture.render(item.mark.get_points()[:3], item._fix_in_frame)


# (Context, unicode, level)
_cached_textures: dict[tuple[mgl.Context, str, int], CharTexture] = {}


class CharTexture:
    @staticmethod
    def get(
        ctx: mgl.Context, unicode: str, standard_outline: np.ndarray, font_size: float
    ) -> CharTexture:
        size_level = math.ceil(font_size / _SIZE_UNIT)
        font_size_of_level = size_level * _SIZE_UNIT

        key = (ctx, unicode, size_level)
        cache = _cached_textures.get(key, None)
        if cache is not None:
            texture = cache
        else:
            texture = CharTexture(ctx, standard_outline, font_size_of_level)
            _cached_textures[key] = texture

        return texture

    def __init__(self, ctx: mgl.Context, standard_outline: np.ndarray, font_size_of_level: float):
        self.ctx = ctx

        pixel_to_frame_ratio = Config.get.default_pixel_to_frame_ratio
        anti_alias_width = Config.get.anti_alias_width

        # 关于这两个的说明，参考 TextChar 中的注释
        self.font_scale_factor = font_size_of_level / ORIG_FONT_SIZE
        frame_scale_factor = pixel_to_frame_ratio / 64

        scale_factor = self.font_scale_factor * frame_scale_factor
        scaled_outline = standard_outline * scale_factor

        box = Cmpt_Points.BoundingBox(scaled_outline)
        x1, y1 = box.data[0, :2] - anti_alias_width
        x2, y2 = box.data[2, :2] + anti_alias_width

        width, height = box.size
        width = math.ceil((x2 - x1) / pixel_to_frame_ratio)
        height = math.ceil((y2 - y1) / pixel_to_frame_ratio)
        self.framebuffer = FrameBuffer(ctx, width, height, (0.2, 0.3, 0.3), True)

        with self.framebuffer.context():
            self.framebuffer.clear()
            # self.render_vitem_standalone(x1, y1, x2, y2, scaled_outline)
            # self.framebuffer.unpremultiply()

        ####

        self.prog = get_program_from_file_prefix('render/shaders/text/pixel_text')
        self.prog['u_fbo'] = 0

        self.u_scale = self.prog['u_scale']
        self.u_char_orig = self.prog['u_char_orig']
        self.u_char_mat = self.prog['u_char_mat']

        self.vbo_coords = ctx.buffer(
            data=np.array(
                [
                    [x1, y2, 0.0, 0.0],  # 左上
                    [x1, y1, 0.0, 1.0],  # 左下
                    [x2, y2, 1.0, 0.0],  # 右上
                    [x2, y1, 1.0, 1.0],  # 右下
                ],
                dtype=np.float32,
            ).tobytes()
        )

        self.vao = ctx.vertex_array(self.prog, self.vbo_coords, 'in_coord', 'in_texcoord')

    def render(self, mark_points: np.ndarray, is_fix_in_frame: bool) -> None:
        camera_info = Renderer.data_ctx.get().camera_info

        if is_fix_in_frame:
            mapped = camera_info.map_fixed_in_frame_points(mark_points)
        else:
            mapped = camera_info.map_points(mark_points)
        orig, right, up = mapped * camera_info.frame_radius
        mat = np.empty((2, 2), dtype=np.float32)
        mat[0] = right - orig  # OpenGL 的矩阵是列主序，所以我们并不是 [:, i] 填充
        mat[1] = up - orig

        self.framebuffer.use(0)
        self.u_scale.value = self.font_scale_factor
        self.u_char_orig.value = orig
        self.u_char_mat.value = mat.flatten()
        self.vao.render(mgl.TRIANGLE_STRIP)
