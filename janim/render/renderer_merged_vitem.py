"""
GPU-driven merged VItem renderer.

Packs all VItem data into contiguous GPU buffers and renders them
in a single instanced draw call, eliminating per-item CPU submission overhead.

Requires OpenGL 4.3+ (compute shaders + SSBOs).
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np

from janim.camera.camera_info import CameraInfo
from janim.render.base import RenderData, Renderer
from janim.render.program import (
    get_compute_shader_from_file,
    get_program_from_file_prefix,
)
from janim.utils.iterables import resize_with_interpolation

if TYPE_CHECKING:
    from janim.items.item import Item
    from janim.items.vitem import VItem


# ItemInfo struct layout (std430):
#   int   point_offset       (4)
#   int   point_count         (4)
#   int   anchor_offset       (4)
#   int   anchor_count         (4)
#   int   fix_in_frame         (4)
#   int   stroke_background    (4)
#   int   is_fill_transparent  (4)
#   int   depth_test           (4)
#   int   shade_in_3d          (4)
#   float glow_size            (4)
#   float _pad0                (4)
#   float _pad1                (4)  => 48 bytes so far
#   vec4  glow_color           (16) => 64
#   vec3  unit_normal          (12)
#   float _pad2                (4)  => 80
#   vec3  start_point          (12)
#   float _pad3                (4)  => 96
ITEM_INFO_SIZE = 96
ITEM_INFO_STRUCT = struct.Struct("<9i3f4f3ff3ff")  # 96 bytes


class MergedVItemRenderer:
    """
    Collects all VItem data for a frame, packs into contiguous SSBOs,
    and renders with a single instanced draw call.
    """

    def __init__(self):
        self._initialized = False

    def _init(self, ctx: mgl.Context):
        self._ctx = ctx
        self._prog = get_program_from_file_prefix(
            "render/shaders/vitem/merged_vitem_plane"
        )
        self._comp = get_compute_shader_from_file(
            "render/shaders/merged_map_points.comp.glsl"
        )

        # SSBOs — start with small reserves, will grow as needed
        self._ssbo_raw_points = ctx.buffer(reserve=64)  # binding 0 for compute input
        self._ssbo_mapped_points = ctx.buffer(
            reserve=64
        )  # binding 0/1 for compute output / render
        self._ssbo_radii = ctx.buffer(reserve=64)  # binding 1
        self._ssbo_colors = ctx.buffer(reserve=64)  # binding 2
        self._ssbo_fills = ctx.buffer(reserve=64)  # binding 3
        self._ssbo_item_infos = ctx.buffer(reserve=64)  # binding 4
        self._ssbo_clip_boxes = ctx.buffer(reserve=64)  # binding 5

        # Empty VAO for instanced drawing (vertices come from gl_VertexID)
        self._vao = ctx.vertex_array(self._prog, [])

        self._u_item_count = self._comp["item_count"]

        self._initialized = True

    def _upload_to_buffer(self, buf: mgl.Buffer, data: bytes) -> None:
        """Upload data to buffer, growing it if needed."""
        size = max(len(data), 4)
        if buf.size != size:
            buf.orphan(size)
        buf.write(data)

    def render_merged(
        self,
        render_data: RenderData,
        vitem_render_list: list[tuple[Item, object]],
    ) -> None:
        """
        Render all VItems in a single instanced draw call.

        vitem_render_list: list of (item_data, render_func) where item_data is a VItem.
        Only VItem instances are processed; others are skipped.
        """
        from janim.items.vitem import VItem

        ctx = render_data.ctx
        if not self._initialized:
            self._init(ctx)

        # Filter to only VItems with enough points, and that use the plane renderer path
        vitems: list[VItem] = []
        for data, _ in vitem_render_list:
            if isinstance(data, VItem) and not data._depth_test:
                points = data.points._points._data
                if points is not None and len(points) >= 3:
                    vitems.append(data)

        if not vitems:
            return

        # --- CPU-side packing ---
        n_items = len(vitems)
        camera_info = render_data.camera_info

        # Pre-calculate total sizes
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
        merged_raw_points = np.zeros((total_points, 4), dtype=np.float32)
        merged_radii_flat = np.zeros(total_anchors, dtype=np.float32)
        merged_colors = np.zeros((total_anchors, 4), dtype=np.float32)
        merged_fills = np.zeros((total_anchors, 4), dtype=np.float32)
        item_infos_bytes = bytearray(n_items * ITEM_INFO_SIZE)
        clip_boxes = np.zeros((n_items, 4, 2), dtype=np.float32)

        point_offset = 0
        anchor_offset = 0

        for i, item in enumerate(vitems):
            pts = item.points._points._data
            n_pts = item_point_counts[i]
            n_anchors = item_anchor_counts[i]

            # Pack raw 3D points
            merged_raw_points[point_offset : point_offset + n_pts, :3] = pts

            # Pack radii (resize to anchor count)
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

            # Compute clip box for this item
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
            # TRIANGLE_STRIP order: bottom-left, top-left, bottom-right, top-right
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
            clip_boxes[i] = cb

            # Build ItemInfo
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
                item_infos_bytes,
                i * ITEM_INFO_SIZE,
                point_offset,
                n_pts,
                anchor_offset,
                n_anchors,
                fix_in_frame,
                stroke_background,
                is_fill_transparent,
                depth_test,
                shade_in_3d,
                glow_size,
                0.0,
                0.0,  # _pad0, _pad1
                glow_rgba[0],
                glow_rgba[1],
                glow_rgba[2],
                glow_rgba[3],
                un[0],
                un[1],
                un[2],
                0.0,  # _pad2
                sp[0],
                sp[1],
                sp[2],
                0.0,  # _pad3
            )

            point_offset += n_pts
            anchor_offset += n_anchors

        # --- Upload to GPU ---
        self._upload_to_buffer(self._ssbo_raw_points, merged_raw_points.tobytes())

        mapped_size = total_points * 16  # vec4 per point
        if self._ssbo_mapped_points.size != mapped_size:
            self._ssbo_mapped_points.orphan(max(mapped_size, 4))

        # Pack radii as vec4 (4 floats per vec4)
        radii_vec4_count = (total_anchors + 3) // 4
        radii_padded = np.zeros(radii_vec4_count * 4, dtype=np.float32)
        radii_padded[:total_anchors] = merged_radii_flat
        self._upload_to_buffer(self._ssbo_radii, radii_padded.tobytes())

        self._upload_to_buffer(self._ssbo_colors, merged_colors.tobytes())
        self._upload_to_buffer(self._ssbo_fills, merged_fills.tobytes())
        self._upload_to_buffer(self._ssbo_item_infos, bytes(item_infos_bytes))

        # Clip boxes: 4 vec2 per item, stored as 2 vec4 per item
        clip_boxes_gpu = np.zeros((n_items * 2, 4), dtype=np.float32)
        for i in range(n_items):
            # box0 = (x0,y0, x1,y1), box1 = (x2,y2, x3,y3)
            clip_boxes_gpu[i * 2] = [
                clip_boxes[i, 0, 0],
                clip_boxes[i, 0, 1],
                clip_boxes[i, 1, 0],
                clip_boxes[i, 1, 1],
            ]
            clip_boxes_gpu[i * 2 + 1] = [
                clip_boxes[i, 2, 0],
                clip_boxes[i, 2, 1],
                clip_boxes[i, 3, 0],
                clip_boxes[i, 3, 1],
            ]
        cb_bytes = clip_boxes_gpu.tobytes()
        self._upload_to_buffer(self._ssbo_clip_boxes, cb_bytes)

        # --- Compute shader: transform all points ---
        self._ssbo_raw_points.bind_to_storage_buffer(0)
        self._ssbo_mapped_points.bind_to_storage_buffer(1)
        self._ssbo_item_infos.bind_to_storage_buffer(2)
        self._u_item_count.value = n_items
        self._comp.run(group_x=(total_points + 255) // 256)

        # --- Render: single instanced draw call ---
        self._ssbo_mapped_points.bind_to_storage_buffer(0)
        self._ssbo_radii.bind_to_storage_buffer(1)
        self._ssbo_colors.bind_to_storage_buffer(2)
        self._ssbo_fills.bind_to_storage_buffer(3)
        self._ssbo_item_infos.bind_to_storage_buffer(4)
        self._ssbo_clip_boxes.bind_to_storage_buffer(5)

        self._vao.render(mgl.TRIANGLE_STRIP, vertices=4, instances=n_items)
