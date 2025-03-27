import os
import shutil
import subprocess as sp
import time
from functools import partial

import OpenGL.GL as gl
from tqdm import tqdm as ProgressDisplay

from janim.anims.timeline import BuiltTimeline, Timeline, TimeRange
from janim.exception import EXITCODE_FFMPEG_NOT_FOUND, ExitException
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.base import create_context
from janim.render.framebuffer import create_framebuffer, framebuffer_context

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

        # PBO 相关初始化
        self.use_pbo = True  # 是否启用PBO优化
        self.pbo_count = 20
        self.pbos = []       # PBO句柄列表
        self.byte_size = pw * ph * 4  # 每帧的字节大小 (RGBA)

        if self.use_pbo:
            self._init_pbos()

    def _init_pbos(self):
        """初始化PBO缓冲区"""
        self.pbos = []
        self.pbos = gl.glGenBuffers(self.pbo_count)
        if not isinstance(self.pbos, (list, tuple)):
            self.pbos = [self.pbos]

        for pbos in self.pbos:
            self.pbos = pbos
            for pbo in pbos:

                gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, pbo)
                    # 分配空间，GL_STREAM_READ表明数据将从GPU读取到CPU，并且每帧都会更新
                gl.glBufferData(gl.GL_PIXEL_PACK_BUFFER, self.byte_size, None, gl.GL_STREAM_READ)

        gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, 0)  # 解绑PBO

    def _cleanup_pbos(self):
        if self.use_pbo and self.pbos.all():
            gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, 0)  # 确保解绑
            # 正确删除多个缓冲区
            gl.glDeleteBuffers(len(self.pbos), self.pbos)
            self.pbos = []

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

        fps = self.built.cfg.fps

        self.open_video_pipe(file_path)

        progress_display = ProgressDisplay(
            range(round(self.built.duration * fps) + 1),
            leave=False,
            dynamic_ncols=True
        )

        rgb = self.built.cfg.background_color.rgb

        transparent = self.ext == '.mov'

        if self.use_pbo:
            # 使用PBO优化的渲染循环
            with framebuffer_context(self.fbo):
                for frame_idx in progress_display:
                    # 渲染当前帧
                    self.fbo.clear(*rgb, not transparent)

                    if transparent:
                        gl.glFlush()

                    self.built.render_all(self.ctx, frame_idx / fps, blend_on=not transparent)

                    # 当前PBO索引和读取PBO索引
                    current_idx = frame_idx % self.pbo_count
                    read_idx = (frame_idx + 1) % self.pbo_count if frame_idx > self.pbo_count - 1 else None

                    # 绑定当前PBO来存储新帧
                    gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, self.pbos[current_idx])
                    # 注意: 当PBO绑定时，最后一个参数是偏移量而不是指针
                    gl.glReadPixels(0, 0, self.built.cfg.pixel_width, self.built.cfg.pixel_height,
                                   gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, 0)

                    # 如果不是第一帧，处理上一帧的数据
                    if read_idx is not None:
                        # 绑定上一个PBO读取数据
                        gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, self.pbos[read_idx])

                        # 使用numpy从映射的内存中读取数据
                        import numpy as np
                        ptr = gl.glMapBuffer(gl.GL_PIXEL_PACK_BUFFER, gl.GL_READ_ONLY)
                        if ptr:
                            # 创建一个numpy数组来引用映射的内存
                            data = np.ctypeslib.as_array(
                                gl.ctypes.cast(ptr, gl.ctypes.POINTER(gl.ctypes.c_ubyte)),
                                shape=(self.byte_size,)
                            )

                            # 写入数据到ffmpeg
                            self.writing_process.stdin.write(data.tobytes())
                            gl.glUnmapBuffer(gl.GL_PIXEL_PACK_BUFFER)

                # 处理最后一帧
                last_idx = frame_idx % self.pbo_count
                gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, self.pbos[last_idx])
                data = gl.glGetBufferSubData(gl.GL_PIXEL_PACK_BUFFER, 0, self.byte_size)
                self.writing_process.stdin.write(data)

                # 最终解绑PBO
                gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, 0)
        else:
            # 原始渲染循环（不使用PBO）
            with framebuffer_context(self.fbo):
                for frame in progress_display:
                    self.fbo.clear(*rgb, not transparent)
                    # 在输出 mov 时，framebuffer 是透明的
                    # 为了颜色能被正确渲染到透明 framebuffer 上
                    # 这里需要禁用自带 blending 的并使用 shader 里自定义的 blending（参考 program.py 的 injection_ja_finish_up）
                    # 但是 shader 里的 blending 依赖 framebuffer 信息
                    # 所以这里需要使用 glFlush 更新 framebuffer 信息使得正确渲染
                    if transparent:
                        gl.glFlush()
                    self.built.render_all(self.ctx, frame / fps, blend_on=not transparent)
                    bytes = self.fbo.read(components=4)
                    self.writing_process.stdin.write(bytes)

        self.close_video_pipe(_keep_temp)

        # 清理PBO资源
        if self.use_pbo:
            self._cleanup_pbos()

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
        stem, self.ext = os.path.splitext(file_path)
        self.final_file_path = file_path
        self.temp_file_path = stem + '_temp' + self.ext

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

        # call ffmpeg to test nvenc/amf support
        test_availability = sp.Popen(
            [self.built.cfg.ffmpeg_bin, '-hide_banner', '-encoders'],
            stdout=sp.PIPE,
            stderr=sp.PIPE
        )
        out, err = test_availability.communicate()
        if b'h264_nvenc' in out:
            command += [
                '-c:v', 'h264_nvenc',
            ]
            log.info(_('Using h264_nvenc for encoding'))
        elif b'h264_amf' in out:
            command += [
                '-c:v', 'h264_amf',
            ]
            log.info(_('Using h264_amf for encoding'))
        else:
            command += [
                '-c:v', 'libx264',
            ]
            log.info(_('No hardware encoder found. Using libx264 for encoding'))

        if self.ext == '.mp4':
            command += [
                '-pix_fmt', 'yuv420p',
            ]
        elif self.ext == '.mov':
            # This is if the background of the exported
            # video should be transparent.
            command += [
                '-vcodec', 'qtrle',
            ]
        elif self.ext == '.gif':
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
