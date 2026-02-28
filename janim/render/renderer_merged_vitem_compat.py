"""
GPU-driven merged VItem renderer (GL 3.3 compatible).

Uses texture buffer objects (TBO) instead of SSBOs, and CPU-side point
transformation instead of compute shaders. Renders all VItems in a single
instanced draw call.
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np
import OpenGL.GL as gl

from janim.render.base import RenderData, Renderer
from janim.render.program import get_program_from_file_prefix
from janim.utils.iterables import resize_with_interpolation

if TYPE_CHECKING:
    from janim.items.item import Item
    from janim.items.vitem import VItem


# ItemInfo TBO layout: 6 vec4 texels per item (96 bytes)
#   texel 0: intBitsToFloat(point_offset, point_count, anchor_offset, anchor_count)
#   texel 1: intBitsToFloat(fix_in_frame, stroke_background, is_fill_transparent, depth_test)
#   texel 2: (shade_in_3d_as_float, glow_size, 0, 0)
#   texel 3: (glow_color.rgba)
#   texel 4: (unit_normal.xyz, 0)
#   texel 5: (start_point.xyz, 0)
ITEM_INFO_TEXELS = 6
ITEM_INFO_BYTES = ITEM_INFO_TEXELS * 16  # 96 bytes

# struct for packing: texel0(4i) + texel1(4i) + texel2(4f) + texel3(4f) + texel4(4f) + texel5(4f)
ITEM_INFO_STRUCT = struct.Struct("<4i4i4f4f4f4f")


class MergedVItemRendererCompat:
    """
    GL 3.3 compatible merged VItem renderer.
    Uses TBOs + instanced drawing instead of SSBOs + compute shaders.
    """

    def __init__(self):
        self._initialized = False

    def _init(self, ctx: mgl.Context):
        self._ctx = ctx
        self._prog = get_program_from_file_prefix(
            "render/shaders/vitem/merged_vitem_plane_compat"
        )

        # Buffers for merged data (backing TBOs)
        self._buf_mapped_points = ctx.buffer(reserve=64)
        self._buf_radii = ctx.buffer(reserve=64)
        self._buf_colors = ctx.buffer(reserve=64)
        self._buf_fills = ctx.buffer(reserve=64)
        self._buf_item_infos = ctx.buffer(reserve=64)

        # Instanced attribute buffers
        self._buf_clip_box0 = ctx.buffer(reserve=64)  # vec4 per instance
        self._buf_clip_box1 = ctx.buffer(reserve=64)  # vec4 per instance
        self._buf_item_idx = ctx.buffer(reserve=64)  # float per instance

        # Create TBO textures via PyOpenGL
        (
            self._tex_points,
            self._tex_radii,
            self._tex_colors,
            self._tex_fills,
            self._tex_item_infos,
        ) = gl.glGenTextures(5)

        # Bind TBOs to their backing buffers
        for tex, buf in [
            (self._tex_points, self._buf_mapped_points),
            (self._tex_radii, self._buf_radii),
            (self._tex_colors, self._buf_colors),
            (self._tex_fills, self._buf_fills),
            (self._tex_item_infos, self._buf_item_infos),
        ]:
            gl.glBindTexture(gl.GL_TEXTURE_BUFFER, tex)
            gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA32F, buf.glo)

        # Get uniform locations for TBO samplers
        self._loc_points = gl.glGetUniformLocation(self._prog.glo, "merged_points")
        self._loc_radii = gl.glGetUniformLocation(self._prog.glo, "merged_radii")
        self._loc_colors = gl.glGetUniformLocation(self._prog.glo, "merged_colors")
        self._loc_fills = gl.glGetUniformLocation(self._prog.glo, "merged_fills")
        self._loc_item_info = gl.glGetUniformLocation(self._prog.glo, "item_info_tbo")

        # Create VAO with instanced attributes
        # We need a dummy per-vertex buffer (4 vertices for TRIANGLE_STRIP)
        # but the actual vertex positions come from instanced clip box attributes
        self._vao = ctx.vertex_array(
            self._prog,
            [
                (self._buf_clip_box0, "4f/i", "in_clip_box0"),
                (self._buf_clip_box1, "4f/i", "in_clip_box1"),
                (self._buf_item_idx, "f/i", "in_item_idx"),
            ],
        )

        self._initialized = True

    def _upload(self, buf: mgl.Buffer, data: bytes) -> None:
        size = max(len(data), 4)
        if buf.size != size:
            buf.orphan(size)
        buf.write(data)

    def render_merged(
        self,
        render_data: RenderData,
        vitem_render_list: list[tuple[Item, object]],
    ) -> None:
        from janim.items.vitem import VItem

        ctx = render_data.ctx
        if not self._initialized:
            self._init(ctx)

        # Filter eligible VItems
        vitems: list[VItem] = []
        for data, _ in vitem_render_list:
            if isinstance(data, VItem) and not data._depth_test:
                points = data.points._points._data
                if points is not None and len(points) >= 3:
                    vitems.append(data)

        if not vitems:
            return

        n_items = len(vitems)
        camera_info = render_data.camera_info

        # Pre-calculate sizes
        total_points = 0
        total_anchors = 0
        item_point_counts = []
        item_anchor_counts = []

        for item in vitems:
            pts = item.points._points._data
            n_pts = len(pts)
            n_anchors = (n_pts + 1) // 2
            item_point_counts.append(n_pts)
            item_anchor_counts.append(n_anchors)
            total_points += n_pts
            total_anchors += n_anchors

        # Allocate merged arrays
        merged_mapped_points = np.zeros((total_points, 4), dtype=np.float32)
        merged_radii_flat = np.zeros(total_anchors, dtype=np.float32)
        merged_colors = np.zeros((total_anchors, 4), dtype=np.float32)
        merged_fills = np.zeros((total_anchors, 4), dtype=np.float32)
        item_infos = bytearray(n_items * ITEM_INFO_BYTES)

        # Instanced attribute data
        clip_box0_data = np.zeros((n_items, 4), dtype=np.float32)
        clip_box1_data = np.zeros((n_items, 4), dtype=np.float32)
        item_idx_data = np.arange(n_items, dtype=np.float32)

        point_offset = 0
        anchor_offset = 0

        for i, item in enumerate(vitems):
            pts = item.points._points._data
            n_pts = item_point_counts[i]
            n_anchors = item_anchor_counts[i]

            # CPU-side point transformation (same as compatibility path)
            if item._fix_in_frame:
                mapped = camera_info.map_fixed_in_frame_points(pts)
            else:
                mapped = camera_info.map_points(pts)
            mapped *= camera_info.frame_radius

            merged_mapped_points[point_offset : point_offset + n_pts, :2] = mapped

            # Pack radii
            radii = resize_with_interpolation(item.radius._radii._data, n_anchors)
            merged_radii_flat[anchor_offset : anchor_offset + n_anchors] = (
                radii.flatten()
            )

            # Pack stroke colors
            stroke = resize_with_interpolation(item.stroke._rgbas._data, n_anchors)
            merged_colors[anchor_offset : anchor_offset + n_anchors] = stroke

            # Pack fill colors
            fill = resize_with_interpolation(item.fill._rgbas._data, n_anchors)
            merged_fills[anchor_offset : anchor_offset + n_anchors] = fill

            # Compute clip box
            corners = np.array(item.points.self_box.get_corners())
            if item._fix_in_frame:
                clip_box = camera_info.map_fixed_in_frame_points(corners)
            else:
                clip_box = camera_info.map_points(corners)
            clip_box *= camera_info.frame_radius

            buff = radii.max() + render_data.anti_alias_radius
            if item.glow._rgba._data[3] != 0.0:
                buff = max(buff, item.glow._size)
            clip_min = np.min(clip_box, axis=0) - buff
            clip_max = np.max(clip_box, axis=0) + buff

            # TRIANGLE_STRIP order: BL, TL, BR, TR
            cb = (
                np.array(
                    [
                        clip_min,
                        [clip_min[0], clip_max[1]],
                        [clip_max[0], clip_min[1]],
                        clip_max,
                    ]
                )
                / camera_info.frame_radius
            )
            cb = np.clip(cb, -1, 1)

            clip_box0_data[i] = [cb[0, 0], cb[0, 1], cb[1, 0], cb[1, 1]]
            clip_box1_data[i] = [cb[2, 0], cb[2, 1], cb[3, 0], cb[3, 1]]

            # Build ItemInfo (6 texels = 96 bytes)
            fix_in_frame = int(item._fix_in_frame)
            stroke_background = int(item.stroke_background)
            is_fill_transparent = int(bool(item.fill.is_transparent()))
            depth_test = int(item._depth_test)
            shade_in_3d = int(item._shade_in_3d)
            glow_size = float(item.glow._size)
            glow_rgba = item.glow._rgba._data.astype(np.float32)

            if depth_test or shade_in_3d:
                un = item.points.unit_normal
                sp = pts[0]
            else:
                un = np.zeros(3, dtype=np.float32)
                sp = np.zeros(3, dtype=np.float32)

            ITEM_INFO_STRUCT.pack_into(
                item_infos,
                i * ITEM_INFO_BYTES,
                # texel 0: offsets (as ints, will be read with floatBitsToInt)
                point_offset,
                n_pts,
                anchor_offset,
                n_anchors,
                # texel 1: flags (as ints)
                fix_in_frame,
                stroke_background,
                is_fill_transparent,
                depth_test,
                # texel 2: shade_in_3d + glow_size (as floats)
                float(shade_in_3d),
                glow_size,
                0.0,
                0.0,
                # texel 3: glow_color
                glow_rgba[0],
                glow_rgba[1],
                glow_rgba[2],
                glow_rgba[3],
                # texel 4: unit_normal
                un[0],
                un[1],
                un[2],
                0.0,
                # texel 5: start_point
                sp[0],
                sp[1],
                sp[2],
                0.0,
            )

            point_offset += n_pts
            anchor_offset += n_anchors

        # --- Upload to GPU ---
        self._upload(self._buf_mapped_points, merged_mapped_points.tobytes())

        # Pack radii as vec4 (4 floats per texel)
        radii_vec4_count = (total_anchors + 3) // 4
        radii_padded = np.zeros(radii_vec4_count * 4, dtype=np.float32)
        radii_padded[:total_anchors] = merged_radii_flat
        self._upload(self._buf_radii, radii_padded.tobytes())

        self._upload(self._buf_colors, merged_colors.tobytes())
        self._upload(self._buf_fills, merged_fills.tobytes())
        self._upload(self._buf_item_infos, bytes(item_infos))

        # Upload instanced attributes
        self._upload(self._buf_clip_box0, clip_box0_data.tobytes())
        self._upload(self._buf_clip_box1, clip_box1_data.tobytes())
        self._upload(self._buf_item_idx, item_idx_data.tobytes())

        # Rebind TBOs after buffer resize (glTexBuffer needs to be called again)
        for tex, buf in [
            (self._tex_points, self._buf_mapped_points),
            (self._tex_radii, self._buf_radii),
            (self._tex_colors, self._buf_colors),
            (self._tex_fills, self._buf_fills),
            (self._tex_item_infos, self._buf_item_infos),
        ]:
            gl.glBindTexture(gl.GL_TEXTURE_BUFFER, tex)
            gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA32F, buf.glo)

        # --- Bind TBO samplers ---
        gl.glUseProgram(self._prog.glo)

        # Use texture units 0-4 for the TBOs
        # (units 15 is used by JA_FRAMEBUFFER, so we stay well below)
        gl.glUniform1i(self._loc_points, 0)
        gl.glUniform1i(self._loc_radii, 1)
        gl.glUniform1i(self._loc_colors, 2)
        gl.glUniform1i(self._loc_fills, 3)
        gl.glUniform1i(self._loc_item_info, 4)

        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self._tex_points)
        gl.glActiveTexture(gl.GL_TEXTURE1)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self._tex_radii)
        gl.glActiveTexture(gl.GL_TEXTURE2)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self._tex_colors)
        gl.glActiveTexture(gl.GL_TEXTURE3)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self._tex_fills)
        gl.glActiveTexture(gl.GL_TEXTURE4)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self._tex_item_infos)

        # --- Recreate VAO if instanced buffers changed size ---
        self._vao = self._ctx.vertex_array(
            self._prog,
            [
                (self._buf_clip_box0, "4f/i", "in_clip_box0"),
                (self._buf_clip_box1, "4f/i", "in_clip_box1"),
                (self._buf_item_idx, "f/i", "in_item_idx"),
            ],
        )

        # --- Single instanced draw call ---
        self._vao.render(mgl.TRIANGLE_STRIP, vertices=4, instances=n_items)
