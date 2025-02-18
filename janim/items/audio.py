
from __future__ import annotations

import copy
import os
import subprocess as sp
from typing import Generator, Iterable, Self

import numpy as np
import numpy.typing as npt

from janim.exception import EXITCODE_FFMPEG_NOT_FOUND, ExitException
from janim.logger import log
from janim.utils.bezier import interpolate
from janim.utils.config import Config
from janim.utils.data import Array
from janim.utils.file_ops import find_file
from janim.utils.iterables import resize_with_interpolation
from janim.utils.simple_functions import clip
from janim.locale.i18n import get_local_strings

_ = get_local_strings('audio')


class Audio:
    '''
    音频

    可以配置 ``audio_channels`` 选项控制读取的声道数（默认为2）

    另见：:class:`~.Config`
    '''

    audio_cache_map: dict[tuple, tuple[np.ndarray, int, str, str]] = {}

    def __init__(self, file_path: str = '', begin: float = -1, end: float = -1, **kwargs):
        super().__init__(**kwargs)
        self._samples = Array(dtype=np.int16)
        self.framerate = 0
        self.file_path = ''
        self.filename = ''
        if file_path:
            self.read(file_path, begin, end)
        else:
            self.framerate = Config.get.audio_framerate

    def copy(self) -> Self:
        copy_audio = copy.copy(self)
        copy_audio._samples = self._samples.copy()
        return copy_audio

    def set_samples(self, data: npt.ArrayLike) -> None:
        self._samples.data = data

    def read(
        self,
        file_path: str,
        begin: float = -1,
        end: float = -1
    ) -> Self:
        '''
        从文件中读取音频

        可以指定 ``begin`` 和 ``end`` 来截取音频的一部分
        '''
        channels = Config.get.audio_channels

        try:
            file_path = find_file(file_path)
        except FileNotFoundError:
            log.warning(
                _('Could not find the audio file "{file_path}". A blank audio of 8 seconds was used instead.')
                .format(file_path=file_path)
            )

            self._samples.data = np.zeros((Config.get.audio_framerate * 8, channels))
            self.framerate = Config.get.audio_framerate
            self.file_path = file_path
            self.filename = os.path.basename(file_path)
            return

        mtime = os.path.getmtime(file_path)
        name = os.path.splitext(os.path.basename(file_path))[0]
        key = (name, mtime, begin, end)

        cached = self.audio_cache_map.get(key, None)
        if cached is not None:
            self._samples.data, self.framerate, self.file_path, self.filename = cached
            return

        command = [
            Config.get.ffmpeg_bin,
            '-vn',
            '-i', file_path,
        ]
        if begin != -1:
            command += ['-ss', str(begin)]  # clip from
        if end != -1:
            command += ['-to', str(end)]    # clip to

        command += [
            '-f', 's16le',
            '-acodec', 'pcm_s16le',
            '-ar', str(Config.get.audio_framerate),     # framerate & samplerate
            '-ac', str(channels),
            '-loglevel', 'error',
            '-',    # output to a pipe
        ]

        try:
            # TODO: support more sampwidth
            # TODO: fix ByteOrder
            with sp.Popen(command, stdout=sp.PIPE) as reading_process:
                data = np.frombuffer(reading_process.stdout.read(), dtype=np.int16)

        except FileNotFoundError:
            log.error(_('Unable to read audio, please install ffmpeg and add it to the environment variables'))
            raise ExitException(EXITCODE_FFMPEG_NOT_FOUND)

        data = data.reshape((-1, channels))

        self._samples.data = data
        self.framerate = Config.get.audio_framerate
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.audio_cache_map[key] = (data, self.framerate, self.file_path, self.filename)

        return self

    def sample_count(self) -> int:
        '''
        所有采样点的数量
        '''
        return len(self._samples.data)

    def duration(self) -> float:
        '''
        持续时间
        '''
        return self.sample_count() / self.framerate

    def clip(self, begin: float = 0, end: float = -1) -> Self:
        '''
        裁剪音频

        - 保留 ``begin`` 到 ``end`` 之间的部分
        - 若 ``begin`` 缺省，则表示从最开始
        - 若 ``end`` 缺省(``-1``)，则表示到最末尾
        '''
        frame_begin = clip(int(begin * self.framerate), 0, self.sample_count())
        if end == -1:
            frame_end = self.sample_count()
        else:
            frame_end = clip(int(end * self.framerate), 0, self.sample_count())
        self._samples.data = self._samples.data[frame_begin:frame_end]

        return self

    def mul(self, value: float | Iterable[float]) -> Self:
        '''
        乘以给定的 ``value``，``value`` 可以含有多个元素（比如一个列表）

        例如：

        - ``audio.mul(0.5)`` 可以使音高减半
        - ``audio.mul([1, 0])`` 可以使开始时最强，结束时最弱
        - ``audio.mul(np.sin(np.linspace(0, 2 * np.pi, audio.sample_count())))`` 可以使音高随时间乘以 sin 函数的一个周期
        '''
        if not isinstance(value, Iterable):
            value = [value]
        value = np.asarray(value)[:, np.newaxis] * np.ones(self._samples.data.shape[1])
        if isinstance(value, Iterable):
            value = resize_with_interpolation(value, self.sample_count())
        self._samples.data = self._samples.data * value

        return self

    def fade_in(self, duration: float) -> Self:
        '''
        应用 ``duration`` 秒的淡入
        '''
        frames = int(self.framerate * duration)
        data = self._samples.data.copy()

        mul = np.linspace(0, 1, frames)
        mul = mul[:, np.newaxis] * np.ones(data.shape[1])

        data[:frames] = (data[:frames] * mul).astype(np.int16)
        self._samples.data = data
        return self

    def fade_out(self, duration: float) -> Self:
        '''
        应用 ``duration`` 秒的淡出
        '''
        frames = int(self.framerate * duration)
        data = self._samples.data.copy()

        mul = np.linspace(1, 0, frames)
        mul = mul[:, np.newaxis] * np.ones(data.shape[1])

        data[-frames:] = (data[-frames:] * mul).astype(np.int16)
        self._samples.data = data
        return self

    def recommended_ranges(
        self,
        *,
        amplitude_threshold_ratio: float = 0.02,
        gap_duration: float = 0.15
    ) -> Generator[tuple[float, float], None, None]:
        '''
        得到若干个可用区段 ``(start, end)``，一般用于配音音频，也就是会忽略没声音的部分，得到有声音的区段的起止时间

        与 :meth:`recommended_range` 的区别是，该方法得到的是若干个区段，
        举个例子，如果在讲了一句话后停了一会，再接着讲，那么前后就会被分成两段

        - ``amplitude_threshould_ratio``: 振幅低于该比率的就认为是没声音的
        - ``gap_duration``: 如果没声音的时长大于该时间，则将前后分段
        '''
        data = np.max(self._samples.data, axis=1)
        indices = np.where(data > np.iinfo(np.int16).max * amplitude_threshold_ratio)[0]
        if len(indices) == 0:
            return

        diff_end_indices = np.where(np.diff(indices) > self.framerate * gap_duration)[0]

        starts = [indices[0], *indices[diff_end_indices + 1]]
        ends = [*indices[diff_end_indices], indices[-1]]

        duration = self.duration()

        starts = interpolate(0, duration, np.array(starts) / len(data))
        ends = interpolate(0, duration, np.array(ends) / len(data))

        yield from zip(starts, ends)

    def recommended_range(
        self,
        *,
        amplitude_threshold_ratio: float = 0.02
    ) -> tuple[float, float] | None:
        '''
        得到可用区段 ``(start, end)``，一般用于配音音频，也就是会忽略没声音的部分，得到有声音的区段的起止时间

        与 :meth:`recommended_ranges` 的区别是，该方法得到的是最开始到最末尾的整个区段

        - ``amplitude_threshould_ratio``: 振幅低于该比率的就认为是没声音的
        '''
        # TODO: cache
        data = np.max(self._samples.data, axis=1)
        indices = np.where(data > np.iinfo(np.int16).max * amplitude_threshold_ratio)[0]
        if len(indices) == 0:
            return None

        duration = self.duration()

        start = interpolate(0, duration, indices[0] / len(data))
        end = interpolate(0, duration, indices[-1] / len(data))

        return start, end
