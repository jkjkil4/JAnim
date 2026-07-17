import os
import subprocess as sp
import sys
from contextlib import contextmanager
from functools import lru_cache
from glob import glob
from queue import Queue
from threading import Thread

import av
import numpy as np
from av.codec.context import ThreadType

from janim.exception import EXITCODE_FFMPEG_NOT_FOUND, ExitException
from janim.locale import get_translator
from janim.logger import log

_ = get_translator('janim.render.encoder')


class PyavVideoEncoder:
    """
    使用 PyAV 编码视频

    不考虑硬件加速检测
    """

    CODEC_CONFIGS = {
        '.mp4': {
            'codec': 'libx264',
            'pix_fmt': 'yuv420p',
            'options': {},
        },
        '.webm': {
            'codec': 'libvpx-vp9',
            'pix_fmt': 'yuva420p',
            'options': {'-auto-alt-ref': '1'},
        },
        '.mov': {
            'codec': 'qtrle',
            'pix_fmt': 'argb',
            'options': {},
        },
        '.gif': {
            'codec': 'gif',
            'pix_fmt': 'rgb8',
            'options': {},
        },
    }

    def open(self, file_path: str, pw: int, ph: int, fps: int) -> None:
        self.file_path = file_path
        self.pw = pw
        self.ph = ph
        self.fps = fps

        ext = os.path.splitext(file_path)[1]
        config = self.CODEC_CONFIGS[ext]

        if ext == '.gif' and fps > 50:
            log.warning(
                _(
                    'GIF export with {fps} FPS (>50) may not play correctly '
                    'because GIF has timing limitations. '
                    'Consider using a lower FPS or another video format.'
                ).format(fps=fps)
            )

        options = {
            'an': '1',  # ffmpeg: -an, no audio
            'crf': '23',  # ffmpeg: -crf, constant rate factor
        }
        options.update(config['options'])

        self.container = av.open(file_path, 'w')
        self.stream: av.VideoStream = self.container.add_stream(
            config['codec'],
            rate=fps,
            options=options,
        )
        self.stream.width = pw
        self.stream.height = ph
        self.stream.pix_fmt = config['pix_fmt']
        self.stream.thread_type = ThreadType.FRAME  # 可以提升处理速度

        self.bytes_queue: Queue[bytes | None] = Queue(maxsize=3)
        self.frame_queue: Queue[av.VideoFrame | None] = Queue(maxsize=3)

        self.frame_thread = Thread(target=self.frame_thread_fn, daemon=True)
        self.frame_thread.start()
        self.encode_thread = Thread(target=self.encode_thread_fn, daemon=True)
        self.encode_thread.start()

    def write(self, data: bytes) -> None:
        self.bytes_queue.put(data)

    def frame_thread_fn(self) -> None:
        while True:
            data = self.bytes_queue.get()
            if data is None:
                self.frame_queue.put(None)
                return

            frame = av.VideoFrame.from_bytes(
                data,
                self.pw,
                self.ph,
                format='rgba',
                flip_vertical=True,
            )
            self.frame_queue.put(frame)

    def encode_thread_fn(self) -> None:
        while True:
            frame = self.frame_queue.get()
            if frame is None:
                for packet in self.stream.encode():
                    self.container.mux(packet)
                return

            for packet in self.stream.encode(frame):
                self.container.mux(packet)

    def finish(self) -> None:
        self.bytes_queue.put(None)
        self.frame_thread.join()
        self.encode_thread.join()
        self.container.close()


class FFmpegH264VideoEncoder:
    """
    使用 FFmpeg bin 编码 H.264 (.mp4) 视频

    考虑硬件加速检测
    """

    def open(self, file_path: str, pw: int, ph: int, fps: int) -> None:
        command = [
            'ffmpeg',
            '-y',  # overwrite output file if it exists
            '-f', 'rawvideo',
            '-s', f'{pw}x{ph}',  # size of one frame
            '-pix_fmt', 'rgba',
            '-r', str(fps),  # frames per second
            '-i', '-',  # The input comes from a pipe
            '-an',  # Tells FFMPEG not to expect any audio
            '-loglevel', 'error',
            *self.format_flags(),
            file_path,
        ]  # fmt: skip

        with self.handle_ffmpeg_not_found():
            self.writing_process = sp.Popen(command, stdin=sp.PIPE)

    def write(self, data: bytes) -> None:
        self.writing_process.stdin.write(data)

    def finish(self) -> None:
        self.writing_process.stdin.close()
        self.writing_process.wait()
        self.writing_process.terminate()

    @staticmethod
    def format_flags() -> list[str]:
        with FFmpegH264VideoEncoder.handle_ffmpeg_not_found():
            encoder = FFmpegH264VideoEncoder.find_encoder()

        log.info(_('Using {encoder} for encoding').format(encoder=encoder))
        return [
            '-pix_fmt', 'yuv420p',
            *FFmpegH264VideoEncoder.encoder_flags(encoder)
        ]  # fmt: skip

    @staticmethod
    @lru_cache(maxsize=1)
    def find_encoder() -> str:
        """查找编码器，优先使用硬件编码器"""
        # Call ffmpeg to enumerate available encoders
        exitcode, output = sp.getstatusoutput('ffmpeg -hide_banner -encoders')
        if exitcode != 0:
            raise FileNotFoundError()

        encoders = [
            'h264_vaapi',
            'h264_nvenc',
            'h264_qsv',
            'h264_amf',
            'h264_videotoolbox',
        ]
        available = [e for e in encoders if e in output]

        # Attempt to use the potential encoder to see if it actually works
        usable = [
            potential
            for potential in available
            if FFmpegH264VideoEncoder.test_encoder_usability(potential)
        ]

        if available:
            log.info(
                _('Hardware encoder probe results:')
                + ' '
                + ', '.join(
                    f'{e}={"ok" if e in usable else "fail"}'  #
                    for e in available
                )
            )

        if usable:
            return usable[0]

        # Safe fallback for if none of the probed hardware encoders work
        log.info(_('No hardware encoder found'))
        return 'libx264'

    @staticmethod
    def test_encoder_usability(potential: str) -> bool:
        exitcode, _ = sp.getstatusoutput(' '.join([
            'ffmpeg',
            '-f', 'lavfi',
            '-i', 'nullsrc=s=640x480:d=0.1',
            *FFmpegH264VideoEncoder.encoder_flags(potential),
            '-f', 'null',
            '-loglevel', 'error',
            '-',
        ]))  # fmt: skip
        return exitcode == 0

    @staticmethod
    def encoder_flags(encoder: str) -> list[str]:
        device = FFmpegH264VideoEncoder.find_encoder_device()
        if encoder == 'h264_vaapi' and device is not None:
            return [
                '-c:v', encoder,
                '-vf', 'vflip,format=nv12,hwupload',
                '-vaapi_device', device,
            ]  # fmt: skip
        else:
            return [
                '-c:v', encoder,
                '-vf', 'vflip,format=nv12'
            ]  # fmt: skip

    @staticmethod
    @lru_cache(maxsize=1)
    def find_encoder_device() -> str | None:
        """返回首个可用的 VA-API 渲染节点，若无则返回 ``None``"""
        # Only applies on linux; exit early on other platforms
        # `linux` and `linux2` are both possible values
        if not sys.platform.startswith('linux'):
            return None

        # If `/dev/dri` doesn't exist, this will just return an empty array
        for device_node in sorted(glob('/dev/dri/renderD*')):
            if os.access(device_node, os.R_OK | os.W_OK):
                return device_node

        return None

    @staticmethod
    @contextmanager
    def handle_ffmpeg_not_found():
        try:
            yield
        except FileNotFoundError:
            log.error(
                _(
                    'Unable to output video. '  #
                    'Hardware acceleration requires FFmpeg to be installed '
                    'and added to PATH.'
                )
            )
            raise ExitException(EXITCODE_FFMPEG_NOT_FOUND)


class PyavAudioEncoder:
    """
    使用 PyAV 编码音频
    """

    def open(self, file_path: str, framerate: int, channels: int) -> None:
        self.file_path = file_path
        self.framerate = framerate
        self.channels = channels

        self.layout = f'{channels}c'

        self.container = av.open(file_path, 'w')
        self.stream: av.AudioStream = self.container.add_stream(
            self.container.default_audio_codec, rate=framerate
        )  # type: ignore
        self.stream.layout = self.layout

    def write(self, array: np.ndarray) -> None:
        frame = av.AudioFrame.from_ndarray(
            array.reshape((1, -1)),  # packed e.g. [[L0,R0,L1,R1,...]]
            format='s16',
            layout=self.layout,
        )
        frame.sample_rate = self.framerate

        for packet in self.stream.encode(frame):
            self.container.mux(packet)

    def finish(self) -> None:
        for packet in self.stream.encode():
            self.container.mux(packet)
        self.container.close()
