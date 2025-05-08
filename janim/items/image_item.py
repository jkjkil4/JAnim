from __future__ import annotations

import io
import math
import os
import subprocess as sp
from bisect import bisect
from functools import lru_cache
from typing import Self

import moderngl as mgl
import numpy as np
from PIL import Image

from janim.components.component import CmptInfo
from janim.components.image import Cmpt_Image
from janim.components.rgbas import Cmpt_Rgbas
from janim.constants import DL, DR, OUT, UL, UR
from janim.exception import (EXITCODE_FFMPEG_NOT_FOUND, EXITCODE_FFPROBE_ERROR,
                             ExitException)
from janim.items.points import Points
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.renderer_imageitem import ImageItemRenderer
from janim.render.renderer_video import VideoRenderer
from janim.render.texture import get_img_from_file
from janim.typing import Alpha, AlphaArray, ColorArray, JAnimColor
from janim.utils.config import Config
from janim.utils.data import AlignedData
from janim.utils.file_ops import find_file
from janim.utils.simple_functions import clip
from janim.utils.space_ops import cross, det, get_norm, z_to_vector

_ = get_local_strings('image_item')


class ImageItem(Points):
    '''
    图像物件

    会读取给定的文件路径的图像
    '''

    renderer_cls = ImageItemRenderer

    image = CmptInfo(Cmpt_Image[Self])
    color = CmptInfo(Cmpt_Rgbas[Self])

    def __init__(
        self,
        file_path_or_image: str | Image.Image,
        *,
        width: float | None = None,
        height: float | None = None,
        min_mag_filter: tuple[int, int] = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR),
        **kwargs
    ):
        super().__init__(**kwargs)

        self.points.set([UL, DL, UR, DR])

        if isinstance(file_path_or_image, str):
            img = get_img_from_file(file_path_or_image)
        else:
            img = file_path_or_image
        self.image.set(img, min_mag_filter)

        if width is None and height is None:
            self.points.set_size(
                img.width * Config.get.default_pixel_to_frame_ratio,
                img.height * Config.get.default_pixel_to_frame_ratio
            )
        elif width is None and height is not None:
            self.points.set_size(
                height * img.width / img.height,
                height
            )
        elif width is not None and height is None:
            self.points.set_size(
                width,
                width * img.height / img.width
            )
        else:   # width is not None and height is not None
            self.points.set_size(width, height)

    def apply_style(
        self,
        color: JAnimColor | ColorArray | None = None,
        alpha: Alpha | AlphaArray | None = None,
        **kwargs
    ) -> Self:
        self.color.set(color, alpha)

        return super().apply_style(**kwargs)

    def get_orig(self) -> np.ndarray:
        '''图像的左上角'''
        return self.points.get()[0]

    def get_horizontal_vect(self) -> np.ndarray:
        '''
        从图像的左上角指向右上角的向量
        '''
        points = self.points.get()
        return points[2] - points[0]

    def get_horizontal_dist(self) -> float:
        '''
        :meth:`get_horizontal_vect` 的长度
        '''
        return get_norm(self.get_horizontal_vect())

    def get_vertical_vect(self) -> np.ndarray:
        '''
        从图像的左上角指向左下角的向量
        '''
        points = self.points.get()
        return points[1] - points[0]

    def get_vertical_dist(self) -> float:
        '''
        :meth:`get_vertical_vect` 的长度
        '''
        return get_norm(self.get_vertical_vect())

    def pixel_to_rgba(self, x: int, y: int) -> np.ndarray:
        '''
        根据像素坐标得到颜色
        '''
        img = self.image.get()
        width, height = img.size
        return np.array(
            img.getpixel((
                clip(x, 0, width - 1),
                clip(y, 0, height - 1)
            ))
        ) / 255

    def point_to_rgba(self, point: np.ndarray, clamp_to_edge: bool = False) -> np.ndarray:
        '''
        通过空间坐标获得对应的像素颜色
        '''
        width, height = self.image.get().size
        x, y = self.point_to_pixel(point)

        if not clamp_to_edge:
            if x < 0 or x >= width or y < 0 or y >= height:
                return np.zeros(4)

        return self.pixel_to_rgba(x, y)

    def pixel_to_point(self, x: float, y: float) -> np.ndarray:
        '''
        通过像素坐标获得对应的空间坐标，可以传入浮点值

        - 例如 ``.pixel_to_point(0, 0)`` 会返回原点位置（图片的左上角）
        - 例如 ``.pixel_to_point(6, 11)`` 会返回 ``(6, 11)`` 像素的左上角
        - 例如 ``.pixel_to_point(6.5, 11.5)`` 会返回 ``(6, 11)`` 像素的中心
        '''
        hor = self.get_horizontal_vect()
        ver = self.get_vertical_vect()
        orig = self.get_orig()
        width, height = self.image.get().size

        return orig + hor * x / width + ver * y / height

    def point_to_pixel(self, point: np.ndarray) -> tuple[int, int]:
        '''
        根据空间坐标得到像素坐标（向图像原点取整）
        '''
        hor = self.get_horizontal_vect()
        ver = self.get_vertical_vect()
        vert = point - self.get_orig()
        normal = cross(hor, ver)

        if not np.isclose(normal, OUT).all():
            hor, ver, vert = (hor, ver, vert) @ z_to_vector(normal)

        u = det(vert, ver) / det(hor, ver)
        v = det(vert, hor) / det(ver, hor)
        width, height = self.image.get().size
        x = math.floor(u * width)
        y = math.floor(v * height)
        return x, y

    @classmethod
    def align_for_interpolate(
        cls,
        item1: ImageItem,
        item2: ImageItem,
    ) -> AlignedData[ImageItem]:
        aligned = super().align_for_interpolate(item1, item2)

        for data in (aligned.data1, aligned.data2):
            points_count = data.points.count()
            data.color.resize(points_count)

        return aligned


class PixelImageItem(ImageItem):
    '''
    图像物件

    与 :class:`ImageItem` 基本一致，只是在图像被放大显示时不进行平滑插值处理，使得像素清晰
    '''
    def __init__(
        self,
        file_path: str,
        *,
        width: float | None = None,
        height: float | None = None,
        min_mag_filter: tuple[int, int] = (mgl.LINEAR_MIPMAP_LINEAR, mgl.NEAREST),
        **kwargs
    ):
        super().__init__(file_path, width=width, height=height, min_mag_filter=min_mag_filter, **kwargs)


class VideoFrame(ImageItem):
    '''
    视频帧，用于提取视频在指定时间处的一帧图像

    - ``file_path``: 文件路径
    - ``frame_at``: 位于哪一帧，可以使用秒数或者 ffmpeg 支持的时间定位方式，例如 ``17.4``、``'00:01:12'`` 等

    不建议使用该类将视频提取为多帧以达到“读取视频”的目的，因为这会导致巨大的性能浪费以及内存占用

    播放视频请使用 :class:`Video`
    '''
    def __init__(
        self,
        file_path: str,
        frame_at: str | float,
        *,
        width: float | None = None,
        height: float | None = None,
        **kwargs
    ):
        super().__init__(self.capture(file_path, frame_at), width=width, height=height, **kwargs)

    @staticmethod
    def capture(file_path: str, frame_at: str | float, *, cache: bool = True) -> Image.Image:
        file_path = find_file(file_path)
        if cache:
            mtime = os.path.getmtime(file_path)
            return VideoFrame._capture_with_cache(mtime, file_path, frame_at)
        else:
            return VideoFrame._capture(file_path, frame_at)

    @lru_cache(maxsize=128)
    @staticmethod
    def _capture_with_cache(mtime: float, file_path: str, frame_at: str | float) -> Image.Image:
        return VideoFrame._capture(file_path, frame_at)

    @staticmethod
    def _capture(file_path: str, frame_at: str | float) -> Image.Image:
        command = [
            Config.get.ffmpeg_bin,
            '-ss', str(frame_at),           # where
            '-i', file_path,     # file
            '-vframes', '1',                # capture only 1 frame
            '-f', 'image2pipe',
            '-vcodec', 'png',
            '-loglevel', 'error',
            '-'     # output to a pipe
        ]

        try:
            with sp.Popen(command, stdout=sp.PIPE) as process:
                data = process.stdout.read()

        except FileNotFoundError:
            log.error(_('Unable to read video frame, please install ffmpeg and add it to the environment variables'))
            raise ExitException(EXITCODE_FFMPEG_NOT_FOUND)

        image = Image.open(io.BytesIO(data))
        return image


class Video(Points):
    '''
    视频物件，和图像物件类似，其实本质上是一个内容实时变化的图像

    控制视频播放的方法：

    - 和其它物件一样，使用 :meth:`~.Item.show` 进行显示，默认暂停在第一帧
    - 调用 :meth:`start` 表示从当前位置开始播放，可以传入 ``speed`` 参数指定倍速
    - 调用 :meth:`stop` 表示停止在当前位置
    - 调用 :meth:`seek` 表示跳转视频进度到指定秒数

    例：

    .. code-block:: python

        video = Video(...).show()

        video.start()

        self.forward()

        video.start(speed=0.5)

        self.forward()

        video.stop()

    表示：先播放 1s，然后以 0.5 倍速播放 1s，然后画面静止
    '''

    color = CmptInfo(Cmpt_Rgbas[Self])

    renderer_cls = VideoRenderer

    def __init__(
        self,
        file_path: str,
        *,
        width: float | None = None,
        height: float | None = None,
        min_mag_filter: tuple[int, int] = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR),
        frame_components: int = 3,
        **kwargs
    ):
        super().__init__(**kwargs)

        from janim.anims.timeline import Timeline
        self.timeline = Timeline.get_context()

        self.file_path = find_file(file_path)
        self.min_mag_filter = min_mag_filter
        self.frame_components = frame_components
        self.info = VideoInfo(self.file_path)

        self.points.set([UL, DL, UR, DR])
        self.actions: list[tuple[float, float, float]] = []

        if width is None and height is None:
            self.points.set_size(
                self.info.width * Config.get.default_pixel_to_frame_ratio,
                self.info.height * Config.get.default_pixel_to_frame_ratio
            )
        elif width is None and height is not None:
            self.points.set_size(
                height * self.info.width / self.info.height,
                height
            )
        elif width is not None and height is None:
            self.points.set_size(
                width,
                width * self.info.height / self.info.width
            )
        else:   # width is not None and height is not None
            self.points.set_size(width, height)

    def apply_style(
        self,
        color: JAnimColor | ColorArray | None = None,
        alpha: Alpha | AlphaArray | None = None,
        **kwargs
    ) -> Self:
        self.color.set(color, alpha)

        return super().apply_style(**kwargs)

    def start(self, *, speed: int = 1) -> Self:
        if not self.actions:
            base = 0
        else:
            x, y, last_speed = self.actions[-1]
            base = y + (self.timeline.current_time - x) * last_speed

        self.actions.append((self.timeline.current_time,
                             base,
                             speed))
        return self

    def stop(self) -> Self:
        self.start(speed=0)
        return self

    def seek(self, t: float) -> Self:
        if not self.actions:
            speed = 0
        else:
            speed = self.actions[-1][2]
        self.actions.append((self.timeline.current_time,
                             t,
                             speed))
        return self

    def compute_time(self, t: float) -> float:
        if not self.actions:
            return 0
        idx = bisect(self.actions, t, key=lambda v: v[0]) - 1
        if idx < 0:
            return 0
        x, y, speed = self.actions[idx]
        return y + (t - x) * speed

    def get_orig(self) -> np.ndarray:
        '''视频的左上角'''
        return self.points.get()[0]

    def get_horizontal_vect(self) -> np.ndarray:
        '''
        从视频的左上角指向右上角的向量
        '''
        points = self.points.get()
        return points[2] - points[0]

    def get_horizontal_dist(self) -> float:
        '''
        :meth:`get_horizontal_vect` 的长度
        '''
        return get_norm(self.get_horizontal_vect())

    def get_vertical_vect(self) -> np.ndarray:
        '''
        从视频的左上角指向左下角的向量
        '''
        points = self.points.get()
        return points[1] - points[0]

    def get_vertical_dist(self) -> float:
        '''
        :meth:`get_vertical_vect` 的长度
        '''
        return get_norm(self.get_vertical_vect())

    def pixel_to_point(self, x: float, y: float) -> np.ndarray:
        '''
        通过像素坐标获得对应的空间坐标，可以传入浮点值

        - 例如 ``.pixel_to_point(0, 0)`` 会返回原点位置（图片的左上角）
        - 例如 ``.pixel_to_point(6, 11)`` 会返回 ``(6, 11)`` 像素的左上角
        - 例如 ``.pixel_to_point(6.5, 11.5)`` 会返回 ``(6, 11)`` 像素的中心
        '''
        hor = self.get_horizontal_vect()
        ver = self.get_vertical_vect()
        orig = self.get_orig()

        return orig + hor * x / self.info.width + ver * y / self.info.height

    @classmethod
    def align_for_interpolate(
        cls,
        item1: ImageItem,
        item2: ImageItem,
    ) -> AlignedData[ImageItem]:
        aligned = super().align_for_interpolate(item1, item2)

        for data in (aligned.data1, aligned.data2):
            points_count = data.points.count()
            data.color.resize(points_count)

        return aligned


class VideoInfo:
    def __init__(self, file_path: str):
        self.file_path = file_path

        command = [
            Config.get.ffprobe_bin,
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate,nb_frames',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0',
            file_path
        ]

        try:
            with sp.Popen(command, stdout=sp.PIPE) as process:
                ret = process.stdout.read().decode('utf-8')
                code = process.wait()
        except FileNotFoundError:
            log.error(_('Unable to read video information, please install ffmpeg'
                        'and add it (including ffprobe) to the environment variables.'))
            raise ExitException(EXITCODE_FFMPEG_NOT_FOUND)

        if code != 0:
            log.error(_('ffprobe error. Please check the output for more information.'))
            raise ExitException(EXITCODE_FFPROBE_ERROR)

        assert ret
        lines = ret.strip().split('\n')
        s_width, s_height, s_fps, s_nb_frames = lines[0].split(',')
        s_duration = lines[1]

        self.width = int(s_width)
        self.height = int(s_height)
        self.fps_num, self.fps_den = map(int, s_fps.split('/'))
        self.nb_frames = int(s_nb_frames)
        self.duration = float(s_duration)


class PixelVideo(Video):
    '''
    视频物件

    与 :class:`Video` 基本一致，只是在被放大显示时不进行平滑插值处理，使得像素清晰
    '''
    def __init__(
        self,
        file_path: str,
        *,
        width: float | None = None,
        height: float | None = None,
        min_mag_filter: tuple[int, int] = (mgl.LINEAR_MIPMAP_LINEAR, mgl.NEAREST),
        **kwargs
    ):
        super().__init__(file_path, width=width, height=height, min_mag_filter=min_mag_filter, **kwargs)
