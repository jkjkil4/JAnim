from __future__ import annotations

import subprocess as sp
from typing import Iterable, Self

import numpy as np

from janim.components.component import Component
from janim.exception import EXITCODE_FFMPEG_NOT_FOUND, ExitException
from janim.logger import log
from janim.utils.config import Config
from janim.utils.iterables import resize_with_interpolation
from janim.utils.simple_functions import clip
from janim.utils.unique_nparray import UniqueNparray


class Cmpt_AudioWav[T](Component[T]):
    def __init__(self):
        self._data = UniqueNparray(dtype=np.int16)
        self._framerate = 0

    def copy(self) -> Self:
        copy_cmpt = super().copy()
        copy_cmpt._data = self._data.copy()
        # _framerate 已在父类中赋值
        return copy_cmpt

    def become(self, other: Cmpt_AudioWav) -> Self:
        self._data = other._data.copy()
        return self

    def __eq__(self, other: Cmpt_AudioWav) -> bool:
        return self._data.is_share(other._data)

    def read(
        self,
        filepath: str,
        begin: float = -1,
        end: float = -1
    ) -> Self:
        command = [
            Config.get.ffmpeg_bin,
            '-vn',
            '-i', filepath,
        ]
        if begin != -1:
            command += ['-ss', str(begin)]  # clip from
        if end != -1:
            command += ['-to', str(end)]    # clip to

        command += [
            '-f', 's16le',
            '-acodec', 'pcm_s16le',
            '-ar', str(Config.get.audio_framerate),     # framerate & samplerate
            '-ac', '1',
            '-loglevel', 'error',
            '-',    # output to a pipe
        ]

        try:
            with sp.Popen(command, stdout=sp.PIPE) as reading_process:
                self._data.data = np.frombuffer(reading_process.stdout.read(), dtype=np.int16)
                self._framerate = Config.get.audio_framerate
        except FileNotFoundError:
            log.error('无法读取音频，需要安装 ffmpeg 并将其添加到环境变量中')
            raise ExitException(EXITCODE_FFMPEG_NOT_FOUND)

    def sample_count(self) -> int:
        return len(self._data._data)

    def duration(self) -> float:
        return self.sample_count() / self._framerate

    def clip(self, begin: float = 0, end: float = -1) -> Self:
        frame_begin = clip(int(begin * self._framerate), 0, self.sample_count())
        if end == -1:
            frame_end = self.sample_count()
        else:
            frame_end = clip(int(end * self._framerate), 0, self.sample_count())
        self._data.data = self._data._data[frame_begin:frame_end]

        return self

    def mul(self, value: float | Iterable[float]) -> Self:
        if isinstance(value, Iterable):
            value = resize_with_interpolation(value, self.sample_count())
        self._data.data = self._data.data * value

        return self

    def fade_in(self, duration: float) -> Self:
        frames = int(self._framerate * duration)
        data = self._data.data
        data[:frames] = (data[:frames] * np.linspace(0, 1, frames)).astype(np.int16)
        self._data.data = data

        return self

    def fade_out(self, duration: float) -> Self:
        frames = int(self._framerate * duration)
        data = self._data.data
        data[-frames:] = (data[-frames:] * np.linspace(1, 0, frames)).astype(np.int16)
        self._data.data = data
