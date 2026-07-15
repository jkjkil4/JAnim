import os
import subprocess as sp
import sys
from contextlib import contextmanager
from functools import lru_cache
from glob import glob

from janim.exception import EXITCODE_FFMPEG_NOT_FOUND, ExitException
from janim.locale import get_translator
from janim.logger import log

_ = get_translator('janim.render.encoder')


class PyavVideoEncoder:
    """
    使用 PyAV 编码视频

    不考虑硬件加速检测
    """

    def open(self, file_path: str, pw: int, ph: int, fps: int) -> None:
        pass

    def write(self, data: bytes) -> None:
        pass

    def finish(self) -> None:
        pass


class FFmpegVideoEncoder:
    """
    使用 FFmpeg bin 编码视频

    考虑硬件加速检测
    """

    def open(self, file_path: str, pw: int, ph: int, fps: int) -> None:
        ext = os.path.splitext(file_path)[1]
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
            *self.ext_specific_flags(ext),
            file_path,
        ]  # fmt: skip

        with handle_ffmpeg_not_found():
            self.writing_process = sp.Popen(command, stdin=sp.PIPE)

    def write(self, data: bytes) -> None:
        self.writing_process.stdin.write(data)

    def finish(self) -> None:
        self.writing_process.stdin.close()
        self.writing_process.wait()
        self.writing_process.terminate()

    @staticmethod
    def ext_specific_flags(ext: str) -> list[str]:
        """针对不同的格式产生不同的 FFMPEG 参数"""
        if ext == '.mp4':
            with handle_ffmpeg_not_found():
                encoder = FFmpegVideoEncoder.find_h264_encoder()
                log.info(_('Using {encoder} for encoding').format(encoder=encoder))
                return [
                    '-pix_fmt', 'yuv420p',
                    *FFmpegVideoEncoder.encoder_flags(encoder)
                ]  # fmt: skip

        if ext == '.mov':
            return [
                '-c:v', 'qtrle',
                '-vf', 'vflip',
            ]  # fmt: skip

        if ext == '.gif':
            return [
                '-vf', 'vflip',
            ]  # fmt: skip

        assert False

    @staticmethod
    @lru_cache(maxsize=1)
    def find_h264_encoder() -> str:
        """查找编码器，优先使用硬件编码器"""
        # Call ffmpeg to enumerate available encoders
        output = sp.getoutput('ffmpeg -hide_banner -encoders')

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
            if FFmpegVideoEncoder.test_encoder_usability(potential)
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
            *FFmpegVideoEncoder.encoder_flags(potential),
            '-f', 'null',
            '-loglevel', 'error',
            '-',
        ]))  # fmt: skip
        return exitcode == 0

    @staticmethod
    def encoder_flags(encoder: str) -> list[str]:
        device = FFmpegVideoEncoder.find_encoder_device()
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


class PyavAudioEncoder:
    """
    使用 PyAV 编码音频
    """

    def open(self, file_path: str, framerate: int, channels: int) -> None:
        pass

    def write(self, data: bytes) -> None:
        pass

    def finish(self) -> None:
        pass


class FFmpegAudioEncoder:
    """
    使用 FFmpeg bin 编码音频（deprecated）
    """

    def open(self, file_path: str, framerate: int, channels: int) -> None:
        command = [
            'ffmpeg',
            '-y',  # overwrite output file if it exists
            '-f', 's16le',
            '-ar', str(framerate),  # framerate & samplerate
            '-ac', str(channels),
            '-i', '-',
            '-loglevel', 'error',
            file_path,
        ]  # fmt: skip

        try:
            self.writing_process = sp.Popen(command, stdin=sp.PIPE)
        except FileNotFoundError:
            log.error(
                _(
                    'Unable to output audio. '  #
                    'Please install ffmpeg and add it to the environment variables.'
                )
            )
            raise ExitException(EXITCODE_FFMPEG_NOT_FOUND)

    def write(self, data: bytes) -> None:
        self.writing_process.stdin.write(data)

    def finish(self) -> None:
        self.writing_process.stdin.close()
        self.writing_process.wait()
        self.writing_process.terminate()


@contextmanager
def handle_ffmpeg_not_found():
    try:
        yield
    except FileNotFoundError:
        log.error(
            _(
                'Unable to output video. '  #
                'Please install ffmpeg and add it to the environment variables.'
            )
        )
        raise ExitException(EXITCODE_FFMPEG_NOT_FOUND)
