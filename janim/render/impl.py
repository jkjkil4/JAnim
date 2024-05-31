
from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np

from janim.render.base import Renderer, get_program
from janim.render.texture import get_texture_from_img
from janim.utils.iterables import resize_with_interpolation

if TYPE_CHECKING:
    from janim.items.image_item import ImageItem
    from janim.items.points import DotCloud
    from janim.items.vitem import VItem


class DotCloudRenderer(Renderer):
    def init(self) -> None:
        self.prog = get_program('render/shaders/dotcloud')

        self.ctx = self.data_ctx.get().ctx
        self.vbo_points = self.ctx.buffer(reserve=1)
        self.vbo_color = self.ctx.buffer(reserve=1)
        self.vbo_radius = self.ctx.buffer(reserve=1)

        self.vao = self.ctx.vertex_array(self.prog, [
            (self.vbo_points, '3f', 'in_point'),
            (self.vbo_color, '4f', 'in_color'),
            (self.vbo_radius, '1f', 'in_radius')
        ])

        self.prev_points = np.array([])
        self.prev_color = np.array([])
        self.prev_radius = np.array([])

    def render(self, item: 'DotCloud') -> None:
        new_color = item.color._rgbas.data
        new_radius = item.radius._radii.data
        new_points = item.points._points.data

        if id(new_color) != id(self.prev_color) or len(new_points) != len(self.prev_points):
            color = resize_with_interpolation(new_color, len(new_points))
            bytes = color.astype('f4').tobytes()

            if len(bytes) != self.vbo_color.size:
                self.vbo_color.orphan(len(bytes))

            self.vbo_color.write(bytes)
            self.prev_color = new_color

        if id(new_radius) != id(self.prev_radius) or len(new_points) != len(self.prev_points):
            radius = resize_with_interpolation(new_radius, len(new_points))
            bytes = radius.astype('f4').tobytes()

            if len(bytes) != self.vbo_radius.size:
                self.vbo_radius.orphan(len(bytes))

            self.vbo_radius.write(bytes)
            self.prev_radius = new_radius

        if id(new_points) != id(self.prev_points):
            bytes = new_points.astype('f4').tobytes()

            if len(bytes) != self.vbo_points.size:
                self.vbo_points.orphan(len(bytes))

            self.vbo_points.write(bytes)
            self.prev_points = new_points

        self.update_fix_in_frame(item, self.prog)
        self.vao.render(mgl.POINTS, vertices=len(self.prev_points))


class VItemRenderer(Renderer):
    def init(self) -> None:
        self.prog = get_program('render/shaders/vitem')

        self.ctx = self.data_ctx.get().ctx
        self.vbo_coord = self.ctx.buffer(reserve=4 * 2 * 4)
        self.vbo_mapped_points = self.ctx.buffer(reserve=1)
        self.vbo_radius = self.ctx.buffer(reserve=1)
        self.vbo_stroke_color = self.ctx.buffer(reserve=1)
        self.vbo_fill_color = self.ctx.buffer(reserve=1)

        self.vao = self.ctx.vertex_array(self.prog, self.vbo_coord, 'in_coord')

        self.prev_camera_info = None

        self.prev_fix_in_frame = None
        self.prev_points = np.array([])
        self.prev_radius = np.array([])
        self.prev_stroke = np.array([])
        self.prev_fill = np.array([])

    def render(self, item: 'VItem') -> None:
        if item.points.curves_count() == 0:
            return
        render_data = self.data_ctx.get()

        new_camera_info = render_data.camera_info

        new_fix_in_frame = item._fix_in_frame
        new_points = item.points._points.data
        new_radius = item.radius._radii.data
        new_stroke = item.stroke._rgbas.data
        new_fill = item.fill._rgbas.data

        is_camera_changed = id(new_camera_info) != id(self.prev_camera_info)

        if new_fix_in_frame != self.prev_fix_in_frame \
                or id(new_radius) != id(self.prev_radius) \
                or id(new_points) != id(self.prev_points) \
                or is_camera_changed:
            if new_fix_in_frame:
                clip_box = render_data.camera_info.map_fixed_in_frame_points(
                    np.array(item.points.self_box.get_corners())
                )
            else:
                clip_box = render_data.camera_info.map_points(item.points.self_box.get_corners())
            clip_box *= render_data.camera_info.frame_radius

            buff = new_radius.max() + render_data.anti_alias_radius
            clip_min = np.min(clip_box, axis=0) - buff
            clip_max = np.max(clip_box, axis=0) + buff
            clip_box = np.array([
                clip_min,
                [clip_min[0], clip_max[1]],
                [clip_max[0], clip_min[1]],
                clip_max
            ]) / render_data.camera_info.frame_radius
            clip_box = np.clip(clip_box, -1, 1)

            bytes = clip_box.astype('f4').tobytes()
            assert len(bytes) == self.vbo_coord.size
            self.vbo_coord.write(bytes)

        if id(new_radius) != id(self.prev_radius) or len(new_points) != len(self.prev_points):
            radius = resize_with_interpolation(new_radius, (len(new_points) + 1) // 2)
            bytes = radius.astype('f4').tobytes()

            if len(bytes) != self.vbo_radius.size:
                self.vbo_radius.orphan(len(bytes))

            self.vbo_radius.write(bytes)
            self.prev_radius = new_radius

        if id(new_stroke) != id(self.prev_stroke) or len(new_points) != len(self.prev_points):
            stroke = resize_with_interpolation(new_stroke, (len(new_points) + 1) // 2)
            bytes = stroke.astype('f4').tobytes()

            if len(bytes) != self.vbo_stroke_color.size:
                self.vbo_stroke_color.orphan(len(bytes))

            self.vbo_stroke_color.write(bytes)
            self.prev_stroke = new_stroke

        if id(new_fill) != id(self.prev_fill) or len(new_points) != len(self.prev_points):
            fill = resize_with_interpolation(new_fill, (len(new_points) + 1) // 2)
            bytes = fill.astype('f4').tobytes()

            if len(bytes) != self.vbo_fill_color.size:
                self.vbo_fill_color.orphan(len(bytes))

            self.vbo_fill_color.write(bytes)
            self.prev_fill = new_fill

        if id(new_points) != id(self.prev_points) \
                or new_fix_in_frame != self.prev_fix_in_frame \
                or is_camera_changed:
            if new_fix_in_frame:
                mapped = render_data.camera_info.map_fixed_in_frame_points(new_points)
            else:
                mapped = render_data.camera_info.map_points(new_points)
            mapped *= render_data.camera_info.frame_radius

            bytes = np.hstack([
                mapped,
                item.points.get_closepath_flags()[:, np.newaxis],
                np.zeros((len(mapped), 1))
            ]).astype('f4').tobytes()

            if len(bytes) != self.vbo_mapped_points.size:
                self.vbo_mapped_points.orphan(len(bytes))

            self.vbo_mapped_points.write(bytes)
            self.prev_fix_in_frame = new_fix_in_frame
            self.prev_camera_info = new_camera_info
            self.prev_points = new_points

        self.vbo_mapped_points.bind_to_storage_buffer(0)
        self.vbo_radius.bind_to_storage_buffer(1)
        self.vbo_stroke_color.bind_to_storage_buffer(2)
        self.vbo_fill_color.bind_to_storage_buffer(3)
        self.vao.render(mgl.TRIANGLE_STRIP)


class ImageItemRenderer(Renderer):
    def init(self) -> None:
        self.prog = get_program('render/shaders/image')

        self.ctx = self.data_ctx.get().ctx
        self.vbo_points = self.ctx.buffer(reserve=4 * 3 * 4)
        self.vbo_color = self.ctx.buffer(reserve=4 * 4 * 4)
        self.vbo_texcoords = self.ctx.buffer(
            data=np.array([
                [0.0, 0.0],     # 左上
                [0.0, 1.0],     # 左下
                [1.0, 0.0],     # 右上
                [1.0, 1.0]      # 右下
            ]).astype('f4').tobytes()
        )

        self.vao = self.ctx.vertex_array(self.prog, [
            (self.vbo_points, '3f', 'in_point'),
            (self.vbo_color, '4f', 'in_color'),
            (self.vbo_texcoords, '2f', 'in_texcoord')
        ])

        self.prev_points = np.array([])
        self.prev_color = np.array([])
        self.prev_img = None

    def render(self, item: 'ImageItem') -> None:
        new_color = item.color._rgbas.data
        new_points = item.points._points.data

        if id(new_color) != id(self.prev_color):
            color = resize_with_interpolation(new_color, 4)
            bytes = color.astype('f4').tobytes()

            assert len(bytes) == self.vbo_color.size

            self.vbo_color.write(bytes)
            self.prev_color = new_color

        if id(new_points) != id(self.prev_points):
            bytes = new_points.astype('f4').tobytes()

            assert len(bytes) == self.vbo_points.size

            self.vbo_points.write(bytes)
            self.prev_points = new_points

        if self.prev_img is None or item.image.img is not self.prev_img:
            self.texture = get_texture_from_img(item.image.get())
            self.texture.build_mipmaps()
            self.prev_img = item.image.img

        self.prog['image'] = 0
        self.texture.filter = item.image.get_filter()
        self.texture.use(0)
        self.update_fix_in_frame(item, self.prog)
        self.vao.render(mgl.TRIANGLE_STRIP)
