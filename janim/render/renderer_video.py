from __future__ import annotations

import subprocess as sp
from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np

from janim.anims.animation import Animation
from janim.exception import EXITCODE_FFMPEG_NOT_FOUND, ExitException
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.base import Renderer
from janim.render.program import get_janim_program
from janim.utils.config import Config
from janim.utils.iterables import resize_with_interpolation

if TYPE_CHECKING:
    from janim.items.image_item import Video, VideoInfo

_ = get_local_strings('renderer_video')


class VideoRenderer(Renderer):
    def __init__(self):
        self.initialized: bool = False

    def init(self) -> None:
        self.prog = get_janim_program('render/shaders/image')

        self.u_fix = self.get_u_fix_in_frame(self.prog)
        self.u_image = self.prog['image']

        self.ctx = self.data_ctx.get().ctx
        self.vbo_points = self.ctx.buffer(reserve=4 * 3 * 4)
        self.vbo_color = self.ctx.buffer(reserve=4 * 4 * 4)
        self.vbo_texcoords = self.ctx.buffer(
            data=np.array([
                [0.0, 0.0],     # 左上
                [0.0, 1.0],     # 左下
                [1.0, 0.0],     # 右上
                [1.0, 1.0]      # 右下
            ], dtype=np.float32).tobytes()
        )

        self.vao = self.ctx.vertex_array(self.prog, [
            (self.vbo_points, '3f', 'in_point'),
            (self.vbo_color, '4f', 'in_color'),
            (self.vbo_texcoords, '2f', 'in_texcoord')
        ])

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
            color = resize_with_interpolation(new_color, 4)
            assert color.dtype == np.float32
            bytes = color.tobytes()

            assert len(bytes) == self.vbo_color.size

            self.vbo_color.write(bytes)
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
        self.vao.render(mgl.TRIANGLE_STRIP)

    def update_texture(self, item: Video) -> None:
        if self.texture is None:
            width, height = item.info.width, item.info.height
            self.texture = self.ctx.texture(
                size=(width, height),
                components=item.frame_components
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
        self.components = components
        self.bufsize = info.height * info.width * self.components

        self.current_frame = -1

        self.process: _Popen | None = None
        self.open_video_pipe(0)

    def get(self, t: float) -> bytes:
        frame = round(t * self.info.fps_num / self.info.fps_den)
        frame = min(frame, self.info.nb_frames - 1)

        if frame > self.current_frame + 10 or frame < self.current_frame:
            self.open_video_pipe(frame)
            self.current_frame = frame - 1

        while frame > self.current_frame:
            raw_frame = self.process.stdout.read(self.bufsize)
            if raw_frame:
                self.raw_frame = raw_frame
            self.current_frame += 1

        return self.raw_frame

    def open_video_pipe(self, frame: int) -> None:
        if self.process is not None:
            self.process.kill()
            self.process.wait()
            self.process = None

        command = [
            Config.get.ffmpeg_bin,
            '-ss', str(frame * self.info.fps_den / self.info.fps_num),
            '-i', self.info.file_path,
            '-f', 'rawvideo',
            '-pix_fmt', 'rgb24' if self.components == 3 else 'rgba',
            '-loglevel', 'error',
            '-'
        ]
        try:
            self.process = _Popen(command, stdout=sp.PIPE)
        except FileNotFoundError:
            log.error(_('Unable to read video. '
                        'Please install ffmpeg and add it to the environment variables.'))
            raise ExitException(EXITCODE_FFMPEG_NOT_FOUND)


class _Popen(sp.Popen):
    def __del__(self) -> None:
        self.kill()
        self.wait()
        super().__del__()
