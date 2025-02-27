import os
import shutil
import subprocess as sp
import time
from functools import partial

from tqdm import tqdm as ProgressDisplay

from janim.anims.timeline import BuiltTimeline, Timeline, TimeRange
from janim.exception import EXITCODE_FFMPEG_NOT_FOUND, ExitException
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.base import create_context, create_framebuffer

_ = get_local_strings('writer')


class VideoWriter:
    '''
    将时间轴动画生成视频输出到文件中

    可以直接调用 ``VideoWriter.writes(MyTimeline().build())`` 进行输出

    主要流程在 :meth:`write_all` 中：

    - 首先调用 ffmpeg，这里用它生成视频（先输出到 _temp 文件中）
    - 然后遍历动画的每一帧，进行渲染，并将像素数据传递给 ffmpeg
    - 最后结束 ffmpeg 的调用，完成 _temp 文件的输出
    - 将 _temp 文件改名，删去 "_temp" 后缀，完成视频输出
    '''
    def __init__(self, built: BuiltTimeline):
        self.built = built
        try:
            self.ctx = create_context(standalone=True, require=430)
        except ValueError:
            self.ctx = create_context(standalone=True, require=330)

        pw, ph = built.cfg.pixel_width, built.cfg.pixel_height
        self.fbo = create_framebuffer(self.ctx, pw, ph)

    @staticmethod
    def writes(built: BuiltTimeline, file_path: str, *, quiet=False) -> None:
        VideoWriter(built).write_all(file_path, quiet=quiet)

    def write_all(self, file_path: str, *, quiet=False, _keep_temp: bool = False) -> None:
        '''将时间轴动画输出到文件中

        - 指定 ``quiet=True``，则不会输出前后的提示信息，但仍有进度条
        '''
        name = self.built.timeline.__class__.__name__
        if not quiet:
            log.info(_('Writing video "{name}"').format(name=name))
            t = time.time()

        self.fbo.use()
        fps = self.built.cfg.fps

        self.open_video_pipe(file_path)

        progress_display = ProgressDisplay(
            range(round(self.built.duration * fps) + 1),
            leave=False,
            dynamic_ncols=True
        )

        rgb = self.built.cfg.background_color.rgb

        for frame in progress_display:
            self.fbo.clear(*rgb)
            self.built.render_all(self.ctx, frame / fps)
            bytes = self.fbo.read(components=4)
            self.writing_process.stdin.write(bytes)

        self.close_video_pipe(_keep_temp)

        if not quiet:
            log.info(
                _('Finished writing video "{name}" in {elapsed:.2f} s')
                .format(name=name, elapsed=time.time() - t)
            )

            if not _keep_temp:
                log.info(
                    _('File saved to "{file_path}" (video only)')
                    .format(file_path=file_path)
                )

    def open_video_pipe(self, file_path: str) -> None:
        stem, ext = os.path.splitext(file_path)
        self.final_file_path = file_path
        self.temp_file_path = stem + '_temp' + ext

        command = [
            self.built.cfg.ffmpeg_bin,
            '-y',   # overwrite output file if it exists
            '-f', 'rawvideo',
            '-s', f'{self.built.cfg.pixel_width}x{self.built.cfg.pixel_height}',  # size of one frame
            '-pix_fmt', 'rgba',
            '-r', str(self.built.cfg.fps),  # frames per second
            '-i', '-',  # The input comes from a pipe
            '-vf', 'vflip',
            '-an',  # Tells FFMPEG not to expect any audio
            '-loglevel', 'error',
        ]

        if ext == '.mp4':
            command += [
                '-vcodec', 'libx264',
                '-pix_fmt', 'yuv420p',
            ]
        elif ext == '.mov':
            # This is if the background of the exported
            # video should be transparent.
            command += [
                '-vcodec', 'qtrle',
            ]
        elif ext == '.gif':
            pass
        else:
            assert False

        command += [self.temp_file_path]
        try:
            self.writing_process = sp.Popen(command, stdin=sp.PIPE)
        except FileNotFoundError:
            log.error(_('Unable to output video. '
                        'Please install ffmpeg and add it to the environment variables.'))
            raise ExitException(EXITCODE_FFMPEG_NOT_FOUND)

    def close_video_pipe(self, _keep_temp: bool) -> None:
        self.writing_process.stdin.close()
        self.writing_process.wait()
        self.writing_process.terminate()
        if not _keep_temp:
            shutil.move(self.temp_file_path, self.final_file_path)


class AudioWriter:
    def __init__(self, built: BuiltTimeline):
        self.built = built

    @staticmethod
    def writes(built: BuiltTimeline, file_path: str, *, quiet=False) -> None:
        AudioWriter(built).write_all(file_path, quiet=quiet)

    def write_all(self, file_path: str, *, quiet=False, _keep_temp: bool = False) -> None:
        name = self.built.timeline.__class__.__name__
        if not quiet:
            log.info(_('Writing audio of "{name}"').format(name=name))
            t = time.time()

        fps = self.built.cfg.fps
        framerate = self.built.cfg.audio_framerate

        self.open_audio_pipe(file_path)

        progress_display = ProgressDisplay(
            range(round(self.built.duration * fps) + 1),
            leave=False,
            dynamic_ncols=True
        )

        get_audio_samples = partial(self.built.get_audio_samples_of_frame,
                                    fps,
                                    framerate)

        for frame in progress_display:
            samples = get_audio_samples(frame)
            self.writing_process.stdin.write(samples.tobytes())

        self.close_audio_pipe(_keep_temp)

        if not quiet:
            log.info(
                _('Finished writing audio of "{name}" in {elapsed:.2f} s')
                .format(name=name, elapsed=time.time() - t)
            )

            if not _keep_temp:
                log.info(
                    _('File saved to "{file_path}"')
                    .format(file_path=file_path)
                )

    def open_audio_pipe(self, file_path: str) -> None:
        stem, ext = os.path.splitext(file_path)
        self.final_file_path = file_path
        self.temp_file_path = stem + '_temp' + ext

        command = [
            self.built.cfg.ffmpeg_bin,
            '-y',   # overwrite output file if it exists
            '-f', 's16le',
            '-ar', str(self.built.cfg.audio_framerate),      # framerate & samplerate
            '-ac', str(self.built.cfg.audio_channels),
            '-i', '-',
            '-loglevel', 'error',
            self.temp_file_path
        ]

        try:
            self.writing_process = sp.Popen(command, stdin=sp.PIPE)
        except FileNotFoundError:
            log.error(_('Unable to output audio. '
                        'Please install ffmpeg and add it to the environment variables.'))
            raise ExitException(EXITCODE_FFMPEG_NOT_FOUND)

    def close_audio_pipe(self, _keep_temp: bool) -> None:
        self.writing_process.stdin.close()
        self.writing_process.wait()
        self.writing_process.terminate()
        if not _keep_temp:
            shutil.move(self.temp_file_path, self.final_file_path)


def merge_video_and_audio(
    ffmpeg_bin: str,
    video_path: str,
    audio_path: str,
    result_path: str,
    remove: bool = True
) -> None:
    command = [
        ffmpeg_bin,
        '-y',
        '-i', video_path,
        '-i', audio_path,
        '-shortest',
        '-c:v', 'copy',
        '-c:a', 'aac',
        result_path,
        '-loglevel', 'error'
    ]

    try:
        merge_process = sp.Popen(command, stdin=sp.PIPE)
    except FileNotFoundError:
        log.error(_('Unable to merge video. '
                    'Please install ffmpeg and add it to the environment variables.'))
        raise ExitException(EXITCODE_FFMPEG_NOT_FOUND)

    merge_process.wait()
    merge_process.terminate()

    if remove:
        os.remove(video_path)
        os.remove(audio_path)

    log.info(
        _('File saved to "{file_path}" (merged)')
        .format(file_path=result_path)
    )


class SRTWriter:
    @staticmethod
    def writes(built: BuiltTimeline, file_path: str) -> None:
        with open(file_path, 'wt') as file:
            chunks: list[tuple[TimeRange, list[Timeline.SubtitleInfo]]] = []

            for info in built.timeline.subtitle_infos:
                if not chunks or chunks[-1][0] != info.range:
                    chunks.append((info.range, []))
                chunks[-1][1].append(info)

            for i, chunk in enumerate(chunks, start=1):
                file.write(f'\n{i}\n')
                file.write(f'{SRTWriter.t_to_srt_time(chunk[0].at)} --> {SRTWriter.t_to_srt_time(chunk[0].end)}\n')
                for info in reversed(chunk[1]):
                    file.write(f'{info.text}\n')

    @staticmethod
    def t_to_srt_time(t: float):
        '''
        将秒数转换为 SRT 时间格式：HH:MM:SS,mmm
        '''
        t = round(t, 3)
        hours = int(t // 3600)
        minutes = int((t % 3600) // 60)
        secs = int(t % 60)
        millis = int((t % 1) * 1000)

        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"
