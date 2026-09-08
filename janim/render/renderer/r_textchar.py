from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np
from janim_backend import compute, gl

from janim.components.points import Cmpt_Points
from janim.render.base import Renderer
from janim.render.framebuffer import FrameBuffer
from janim.render.program import get_program_from_file_prefix
from janim.render.renderer.r_vitem import VItemRenderer
from janim.render.shader import find_shader_file, resolve_shader_from_file
from janim.utils.config import Config
from janim.utils.font.database import ORIG_FONT_SIZE

if TYPE_CHECKING:
    from janim.items.text import TextChar

_SIZE_UNIT = 12


class TextCharRenderer(VItemRenderer):
    def render(self, item: TextChar) -> None:  # type: ignore
        if item._pixel_render_info is None:
            super().render(item)
        else:
            item._pixel_render_info.render(item)


class PixelRenderInfo:
    """
    存储 ``render='pixel'`` 绘制模式需要用到的信息，并在 :class:`TextCharRenderer` 中被调用以渲染

    :param unicode: 字符的 unicode
    :param standard_outline: 该字符所对应的标准 outline，即 :meth:`~.Font.get_glyph_data` 的返回值
    :param font_size: 当前指定的字号
    """

    def __init__(self, unicode: str, standard_outline: np.ndarray, font_size: float):
        self.unicode = unicode
        self.standard_outline = standard_outline
        self.font_size = font_size

        self._initialized: bool = False
        self._is_null = len(standard_outline) == 0

    def init(self) -> None:
        self.ctx = Renderer.data_ctx.get().ctx

        self.cfbo = _get_char_framebuffer(
            self.ctx, self.unicode, self.standard_outline, self.font_size
        )

        self.prog = get_program_from_file_prefix('render/shaders/text/pixel_text')
        self.prog['u_fbo'] = 0

        self.u_scale, self.u_char_orig, self.u_char_mat, self.u_rgba = Renderer.uniforms(
            self.prog,
            ('u_scale', gl.GL_FLOAT),
            ('u_char_orig', gl.GL_FLOAT_VEC2),
            ('u_char_mat', gl.GL_FLOAT_MAT2),
            ('u_rgba', gl.GL_FLOAT_VEC4),
        )

        self.vao = self.ctx.vertex_array(self.prog, self.cfbo.vbo_coords, 'in_coord', 'in_texcoord')

    def render(self, item: TextChar) -> None:
        if self._is_null:
            return

        if not self._initialized:
            self.init()
            self._initialized = True

        camera_info = Renderer.data_ctx.get().camera_info
        mark_points = item.mark.get_points()[:3]

        if item._fix_in_frame:
            mapped = camera_info.map_fixed_in_frame_points(mark_points)
        else:
            mapped = camera_info.map_points(mark_points)
        orig_bytes, mat_bytes = compute.compute_pixelchar_uniform_bytes(
            mapped,
            camera_info.frame_radius,
        )

        self.cfbo.framebuffer.use(0)

        self.u_scale.write_float(self.cfbo.font_scale_factor)
        self.u_char_orig.write_bytes(orig_bytes)
        self.u_char_mat.write_bytes(mat_bytes)

        self.u_rgba.write_bytes(item.fill._rgbas._data[0].tobytes())

        self.vao.render(mgl.TRIANGLE_STRIP)


# (Context, unicode, level)
_cached_framebuffers: dict[tuple[mgl.Context, str, int], CharFrameBuffer] = {}


@dataclass(slots=True)
class CharFrameBuffer:
    framebuffer: FrameBuffer
    vbo_coords: mgl.Buffer
    font_scale_factor: float


def _get_char_framebuffer(
    ctx: mgl.Context, unicode: str, standard_outline: np.ndarray, font_size: float
) -> CharFrameBuffer:
    size_level = math.ceil(font_size / _SIZE_UNIT)
    font_size_of_level = size_level * _SIZE_UNIT

    key = (ctx, unicode, size_level)
    cache = _cached_framebuffers.get(key, None)
    if cache is not None:
        result = cache
    else:
        result = _compute_char_framebuffer(ctx, standard_outline, font_size_of_level)
        _cached_framebuffers[key] = result

    return result


def _compute_char_framebuffer(
    ctx: mgl.Context, standard_outline: np.ndarray, font_size_of_level: float
) -> CharFrameBuffer:
    pixel_to_frame_ratio = Config.get.default_pixel_to_frame_ratio
    anti_alias_width = Config.get.anti_alias_width

    # 关于这两个的说明，参考 TextChar 中的注释
    font_scale_factor = font_size_of_level / ORIG_FONT_SIZE
    frame_scale_factor = pixel_to_frame_ratio / 64

    scale_factor = font_scale_factor * frame_scale_factor
    scaled_outline = standard_outline * scale_factor

    box = Cmpt_Points.BoundingBox(scaled_outline)
    x1, y1 = box.data[0, :2] - anti_alias_width
    x2, y2 = box.data[2, :2] + anti_alias_width

    width, height = box.size
    width = math.ceil((x2 - x1) / pixel_to_frame_ratio)
    height = math.ceil((y2 - y1) / pixel_to_frame_ratio)
    framebuffer = FrameBuffer(ctx, width, height, (0, 0, 0), True)

    # 在 standalone 和 pixelchar 绘制中均有用到
    vbo_coords = ctx.buffer(
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

    with framebuffer.context():
        framebuffer.clear()
        _render_vitem_standalone(ctx, vbo_coords, scaled_outline)

    return CharFrameBuffer(framebuffer, vbo_coords, font_scale_factor)


def _render_vitem_standalone(
    ctx: mgl.Context,
    vbo_coords: mgl.Buffer,
    scaled_outline: np.ndarray,
) -> None:
    compatibility = ctx.version_code < 430

    cache = CharTexture._cached_standalone_prog.get(ctx, None)
    if cache is not None:
        prog = cache
    else:
        suffix = 'compa' if compatibility else 'normal'
        prog = ctx.program(
            vertex_shader=resolve_shader_from_file(
                find_shader_file(f'render/shaders/text/_vitem_standalone_{suffix}_.vert.glsl')
            ),
            fragment_shader=resolve_shader_from_file(
                find_shader_file(f'render/shaders/text/_vitem_standalone_{suffix}_.frag.glsl')
            ),
        )
        CharTexture._cached_standalone_prog[ctx] = prog

    outline_bytes = scaled_outline[:, :2].astype(np.float32).tobytes()
    if compatibility:
        bytes_len = len(outline_bytes)
        size = (bytes_len + 15) & ~15  # align vec4
        if bytes_len != size:
            outline_bytes += bytes(size - bytes_len)
        vbo_points = ctx.buffer(data=outline_bytes)
    else:
        vbo_points = ctx.buffer(data=outline_bytes)

    vao = ctx.vertex_array(prog, vbo_coords, 'in_coord', 'in_texcoord')

    prog['u_anti_alias_radius'] = Config.get.anti_alias_width / 2
    prog['lim'] = (len(scaled_outline) - 1) // 2 * 2

    if compatibility:
        (sampb_points,) = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, sampb_points)
        gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA32F, vbo_points.glo)
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, sampb_points)
    else:
        vbo_points.bind_to_storage_buffer(0)
    vao.render(mgl.TRIANGLE_STRIP)


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
        self.framebuffer = FrameBuffer(ctx, width, height, (0, 0, 0), True)

        # 在 standalone 和 pixelchar 绘制中均有用到
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

        with self.framebuffer.context():
            self.framebuffer.clear()
            self._render_vitem_standalone(ctx, self.vbo_coords, scaled_outline)

        ####

        self.prog = get_program_from_file_prefix('render/shaders/text/pixel_text')
        self.prog['u_fbo'] = 0

        self.u_scale, self.u_char_orig, self.u_char_mat, self.u_rgba = Renderer.uniforms(
            self.prog,
            ('u_scale', gl.GL_FLOAT),
            ('u_char_orig', gl.GL_FLOAT_VEC2),
            ('u_char_mat', gl.GL_FLOAT_MAT2),
            ('u_rgba', gl.GL_FLOAT_VEC4),
        )

        self.vao = ctx.vertex_array(self.prog, self.vbo_coords, 'in_coord', 'in_texcoord')

    def render(self, mark_points: np.ndarray, is_fix_in_frame: bool, rgba: np.ndarray) -> None:
        camera_info = Renderer.data_ctx.get().camera_info

        if is_fix_in_frame:
            mapped = camera_info.map_fixed_in_frame_points(mark_points)
        else:
            mapped = camera_info.map_points(mark_points)
        orig_bytes, mat_bytes = compute.compute_pixelchar_uniform_bytes(
            mapped,
            camera_info.frame_radius,
        )

        self.framebuffer.use(0)

        self.u_scale.write_float(self.font_scale_factor)
        self.u_char_orig.write_bytes(orig_bytes)
        self.u_char_mat.write_bytes(mat_bytes)

        self.u_rgba.write_bytes(rgba.tobytes())

        self.vao.render(mgl.TRIANGLE_STRIP)

    _cached_standalone_prog: dict[mgl.Context, mgl.Program] = {}

    @staticmethod
    def _render_vitem_standalone(
        ctx: mgl.Context,
        vbo_coords: mgl.Buffer,
        scaled_outline: np.ndarray,
    ) -> None:
        compatibility = ctx.version_code < 430

        cache = CharTexture._cached_standalone_prog.get(ctx, None)
        if cache is not None:
            prog = cache
        else:
            suffix = 'compa' if compatibility else 'normal'
            prog = ctx.program(
                vertex_shader=resolve_shader_from_file(
                    find_shader_file(f'render/shaders/text/_vitem_standalone_{suffix}_.vert.glsl')
                ),
                fragment_shader=resolve_shader_from_file(
                    find_shader_file(f'render/shaders/text/_vitem_standalone_{suffix}_.frag.glsl')
                ),
            )
            CharTexture._cached_standalone_prog[ctx] = prog

        outline_bytes = scaled_outline[:, :2].astype(np.float32).tobytes()
        if compatibility:
            bytes_len = len(outline_bytes)
            size = (bytes_len + 15) & ~15  # align vec4
            if bytes_len != size:
                outline_bytes += bytes(size - bytes_len)
            vbo_points = ctx.buffer(data=outline_bytes)
        else:
            vbo_points = ctx.buffer(data=outline_bytes)

        vao = ctx.vertex_array(prog, vbo_coords, 'in_coord', 'in_texcoord')

        vbo_points.bind_to_storage_buffer(0)
        prog['u_anti_alias_radius'] = Config.get.anti_alias_width / 2
        prog['lim'] = (len(scaled_outline) - 1) // 2 * 2

        if compatibility:
            (sampb_points,) = gl.glGenTextures(1)
            gl.glBindTexture(gl.GL_TEXTURE_BUFFER, sampb_points)
            gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA32F, vbo_points.glo)
            gl.glActiveTexture(gl.GL_TEXTURE0)
            gl.glBindTexture(gl.GL_TEXTURE_BUFFER, sampb_points)
        vao.render(mgl.TRIANGLE_STRIP)
