from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Any, Callable

import av
import moderngl as mgl
import numpy as np
from av.codec.context import ThreadType

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


@dataclass(slots=True)
class FrameData:
    frame: Any
    data: bytes | None = None


class VideoReader:
    def __init__(self, info: VideoInfo, components: int):
        # 基础信息
        assert components in (3, 4)
        self.info = info
        self.format = 'rgb24' if components == 3 else 'rgba'

        # PyAV 相关结构
        self.container = av.open(info.file_path)
        self.stream = self.container.streams.video[0]  # VideoInfo 中确认过存在视频流，这里不用检查
        self.stream.thread_type = ThreadType.FRAME
        self.time_base: Fraction = self.stream.time_base  # type: ignore

        # 已经解码的帧，若最后一个元素为 None，则表示到达视频末尾
        # seek 时，会将 keyframe-pts ~ pts 的帧以及 pts 后的一帧一并存入列表
        # next 时，行为类似队列，会将后续的帧加入列表末尾，并弹出列表开头的帧
        self.frames: list[FrameData] = []
        self.worker = DecodeWorker(self._worker_task)  # 用于预先解析

        # 表示在 get 时，这次的时刻超出前一次时刻的容许量，如果超出则触发 seek
        self.pts_tolerance = self.time_to_pts(10)

    def get(self, t: float) -> bytes:
        pts = self.time_to_pts(t)
        self.ensure_frames_correct(pts)
        return self._get_frame_bytes(self.frames[self.active_index])

    def _get_frame_bytes(self, frame_data: FrameData) -> bytes:
        try:
            if frame_data.data is None:
                frame_bytes: bytes = frame_data.frame.to_ndarray(format=self.format).tobytes()
                frame_data.data = frame_bytes
            return frame_data.data
        except Exception:
            print(len(self.frames))
            raise

    def time_to_pts(self, t: float) -> int:
        """
        将实际时间转换为视频流时间戳
        """
        return math.ceil(int(t / self.time_base))

    def ensure_frames_correct(self, pts: int) -> None:
        """
        保证 ``pts`` 一定满足 ``frames[-2].pts <= pts < frames[-1].pts``
        - 如果 ``pts`` 处于已解码区域的后面，但是没有超出太多（由 ``self.pts_tolerance`` 决定），则让已解码区域逐渐后挪
        - 如果 ``pts`` 处于已解码区域的前面，或处于后面超出太多，则 ``seek`` 重新构建已解码区域
        """
        needs_seek = self.needs_seek(pts)
        if needs_seek:
            # 等待运行中的解析结束
            self.worker.get()
            self.worker.clear()
            # seek 视频流并解析首两帧（非精准定位，会稍前一些）
            self.container.seek(pts, stream=self.stream)
            self.decode_iter = iter(self.container.decode(self.stream))
            frame1 = next(self.decode_iter)
            frame2 = next(self.decode_iter, None)
            self.frames = [FrameData(frame1), FrameData(frame2)]
            self.active_index = 0  # 倒数第二个

        # 目前，`pts` 不位于已解码区域前面，现在判断如果在已解码区域后面，则让已解码区域逐渐后挪
        if self.frames[-1].frame is not None and self.frames[-1].frame.pts <= pts:
            worker_result = self.worker.get()

            while self.frames[-1].frame is not None and self.frames[-1].frame.pts <= pts:
                # 如果有预先解析好的帧，则利用，否则手动 next
                if worker_result is not None:
                    next_frame = worker_result
                    worker_result = None
                    self.worker.clear()
                else:
                    next_frame = FrameData(next(self.decode_iter, None))

                if not needs_seek:
                    self.frames.pop(0)
                self.frames.append(next_frame)

            # 注册预先解析任务
            if self.frames[-1].frame is not None:
                self.worker.submit()

            self.active_index = len(self.frames) - 2  # 倒数第二个

        # 目前，`pts` 一定位于已解码区域内部，根据 pts 对应其中的哪个 frame，更新记录的 active_index 下标
        # 因为更新后的下标很可能差得不多，所以这里直接 while 而非二分
        while pts < self.frames[self.active_index].frame.pts:
            assert self.active_index != 0
            self.active_index -= 1
        while (
            self.frames[self.active_index + 1].frame is not None
            and pts >= self.frames[self.active_index + 1].frame.pts
        ):
            assert self.active_index != len(self.frames) - 2
            self.active_index += 1

    def needs_seek(self, pts: int) -> bool:
        if len(self.frames) < 2:
            return True
        if pts < self.frames[0].frame.pts:
            return True
        return (
            self.frames[-1].frame is not None
            and pts >= self.frames[-2].frame.pts + self.pts_tolerance
        )

    def _worker_task(self) -> FrameData | None:
        frame_data = FrameData(next(self.decode_iter, None))
        if frame_data.frame is not None:
            self._get_frame_bytes(frame_data)  # 在子线程中预先计算 bytes
        return frame_data


class DecodeWorker:
    def __init__(self, task: Callable[[], FrameData | None]):
        self._task = task
        self._result: FrameData | None = None

        self._ready = threading.Event()
        self._done = threading.Event()
        self._done.set()

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while True:
            self._ready.wait()
            self._ready.clear()

            self._result = self._task()

            self._done.set()

    def submit(self):
        assert self._done.is_set(), 'worker already has a running task'
        self._done.clear()
        self._ready.set()

    def get(self):
        self._done.wait()
        return self._result

    def clear(self):
        self._result = None
