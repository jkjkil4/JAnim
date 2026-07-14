from __future__ import annotations

from fractions import Fraction
import math
from typing import TYPE_CHECKING

import av
import moderngl as mgl
import numpy as np

from janim.anims.animation import Animation
from janim.locale import get_translator
from janim.render.base import Renderer
from janim.render.program import get_program_from_file_prefix

if TYPE_CHECKING:
    from janim.items.image_item import Video, VideoInfo

_ = get_translator('janim.render.renderer_video')


class VideoRenderer(Renderer):
    def __init__(self):
        self.initialized: bool = False

    def init(self) -> None:
        self.prog = get_program_from_file_prefix('render/shaders/image')

        self.u_fix = self.get_u_fix_in_frame(self.prog)
        self.u_image = self.prog['image']

        self.ctx = self.data_ctx.get().ctx
        self.vbo_points = self.ctx.buffer(reserve=4 * 3 * 4)
        self.vbo_color = self.ctx.buffer(reserve=4 * 4 * 4)
        self.vbo_texcoords = self.ctx.buffer(
            data=np.array(
                [
                    [0.0, 0.0],  # 左上
                    [0.0, 1.0],  # 左下
                    [1.0, 0.0],  # 右上
                    [1.0, 1.0],  # 右下
                ],
                dtype=np.float32,
            ).tobytes()
        )

        self.vao = self.ctx.vertex_array(
            self.prog,
            [
                (self.vbo_points, '3f', 'in_point'),
                (self.vbo_color, '4f', 'in_color'),
                (self.vbo_texcoords, '2f', 'in_texcoord'),
            ],
        )

        self.texture: mgl.Texture | None = None
        self.reader: VideoReader | None = None

        self.prev_points = None
        self.prev_color = None

    def render(self, item: Video) -> None:
        if not self.initialized:
            self.init()
            self.initialized = True

        new_color = item.color._rgbas.data
        new_points = item.points._points.data

        if new_color is not self.prev_color:
            self.update_static_buffer_data(new_color, self.vbo_color, 4)
            self.prev_color = new_color

        if new_points is not self.prev_points:
            assert new_points.dtype == np.float32
            bytes = new_points.tobytes()

            assert len(bytes) == self.vbo_points.size

            self.vbo_points.write(bytes)
            self.prev_points = new_points

        self.update_texture(item)
        self.u_image.value = 0
        self.texture.filter = item.min_mag_filter
        self.texture.use(0)
        self.update_fix_in_frame(self.u_fix, item)

        with self.depth_test_if_enabled(self.ctx, item):
            self.vao.render(mgl.TRIANGLE_STRIP)

    def update_texture(self, item: Video) -> None:
        if self.texture is None:
            width, height = item.info.width, item.info.height
            self.texture = self.ctx.texture(
                size=(width, height),
                components=item.frame_components,
            )
            self.texture.repeat_x = False
            self.texture.repeat_y = False

        if self.reader is None or self.reader.info is not item.info:
            self.reader = VideoReader(item.info, item.frame_components)
            self.prev_frame: bytes | None = None

        global_t = Animation.global_t_ctx.get()
        raw_frame = self.reader.get(item.compute_time(global_t, item.info.duration))
        if raw_frame is not self.prev_frame:
            self.texture.write(raw_frame)
            self.texture.build_mipmaps()
            self.prev_frame = raw_frame


class VideoReader:
    def __init__(self, info: VideoInfo, components: int):
        assert components in (3, 4)
        self.info = info
        self.format = 'rgb24' if components == 3 else 'rgba'

        self.container = av.open(info.file_path)
        self.stream = self.container.streams.video[0]  # VideoInfo 中已经确认过存在视频流
        self.time_base: Fraction = self.stream.time_base  # type: ignore

        # 两帧：(刚播放的帧, 随后的下一帧)
        self.frame_pair: tuple[av.VideoFrame, av.VideoFrame | None] | None = None
        # bytes 缓存，会因为 seek 和 next 重置
        self.bytes_cache: bytes | None = None

        # get 时刻超出前一次时刻的容许量，超出则触发 seek
        self.pts_tolerance = self.time_to_pts(10)

    def get(self, t: float) -> bytes:
        pts = self.time_to_pts(t)
        if self.needs_seek(pts):
            self.seek(pts)

        assert self.frame_pair is not None

        while self.frame_pair[1] is not None and self.frame_pair[1].pts <= pts:  # type: ignore
            self.next()

        if self.bytes_cache is None:
            self.bytes_cache = self.frame_pair[0].to_ndarray(format=self.format).tobytes()
        return self.bytes_cache

    def time_to_pts(self, t: float) -> int:
        return math.ceil(int(t / self.time_base))

    def needs_seek(self, pts: int) -> bool:
        if self.frame_pair is None:
            return True
        return not (0 <= pts - self.frame_pair[0].pts < self.pts_tolerance)  # type: ignore

    def seek(self, pts: int) -> None:
        self.container.seek(pts, stream=self.stream)
        self.decode_iter = iter(self.container.decode(self.stream))

        frame1 = next(self.decode_iter)
        frame2 = next(self.decode_iter, None)
        self.frame_pair = (frame1, frame2)
        self.bytes_cache = None

    def next(self) -> None:
        assert self.frame_pair is not None

        frame = next(self.decode_iter, None)
        if frame is None and self.frame_pair[1] is None:
            return

        self.frame_pair = (self.frame_pair[1], frame)  # type: ignore
        self.bytes_cache = None
