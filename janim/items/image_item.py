from __future__ import annotations

import io
import math
import subprocess as sp
from typing import Self

import moderngl as mgl
import numpy as np
from PIL import Image

from janim.components.component import CmptInfo
from janim.components.image import Cmpt_Image
from janim.components.rgbas import Cmpt_Rgbas
from janim.constants import DL, DR, OUT, UL, UR
from janim.exception import EXITCODE_FFMPEG_NOT_FOUND, ExitException
from janim.items.points import Points
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.impl import ImageItemRenderer
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

    image = CmptInfo(Cmpt_Image)
    color = CmptInfo(Cmpt_Rgbas)

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
        self.min_mag_filter = min_mag_filter

        self.points.set([UL, DL, UR, DR])

        if isinstance(file_path_or_image, str):
            img = get_img_from_file(file_path_or_image)
        else:
            img = file_path_or_image
        self.image.set(img, min_mag_filter)

        if width is None and height is None:
            self.points.set_size(
                img.width * Config.get.pixel_to_frame_ratio,
                img.height * Config.get.pixel_to_frame_ratio
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

    def set_style(
        self,
        color: JAnimColor | ColorArray | None = None,
        alpha: Alpha | AlphaArray | None = None,
        **kwargs
    ) -> Self:
        self.color.set(color, alpha)

        return super().set_style(**kwargs)

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
        hor = self.get_horizontal_vect()
        ver = self.get_vertical_vect()
        vert = point - self.get_orig()
        normal = cross(hor, ver)

        if not np.isclose(normal, OUT).all():
            hor, ver, vert = np.dot((hor, ver, vert), z_to_vector(normal))

        u = det(vert, ver) / det(hor, ver)
        v = det(vert, hor) / det(ver, hor)
        width, height = self.image.get().size
        x = math.floor(u * width)
        y = math.floor(v * height)

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
    def capture(file_path: str, frame_at: str | float) -> Image.Image:
        command = [
            Config.get.ffmpeg_bin,
            '-ss', str(frame_at),           # where
            '-i', find_file(file_path),     # file
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
