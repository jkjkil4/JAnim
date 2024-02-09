import os
import shutil
import subprocess as sp
import time

import moderngl as mgl
from tqdm import tqdm as ProgressDisplay

from janim.anims.timeline import TimelineAnim
from janim.logger import log
from janim.utils.config import Config


class FileWriter:
    def __init__(self, anim: TimelineAnim):
        self.anim = anim
        self.ctx = mgl.create_standalone_context()
        self.ctx.enable(mgl.BLEND)

        pw, ph = Config.get.pixel_width, Config.get.pixel_height
        self.fbo = self.ctx.framebuffer(
            color_attachments=self.ctx.texture(
                (pw, ph),
                components=4,
                samples=0,
            ),
            depth_attachment=self.ctx.depth_renderbuffer(
                (pw, ph),
                samples=0
            )
        )

    def write_all(self, file_path: str) -> None:
        name = self.anim.timeline.__class__.__name__
        log.info(f'Writing "{name}"')
        t = time.time()

        self.fbo.use()
        fps = Config.get.fps

        self.open_video_pipe(file_path)

        progress_display = ProgressDisplay(
            range(round(self.anim.global_range.duration * fps) + 1),
            leave=False,
            dynamic_ncols=True
        )

        for frame in progress_display:
            self.fbo.clear()    # TODO: backgound-color
            self.anim.anim_on(frame / fps)
            self.anim.render_all(self.ctx)
            bytes = self.fbo.read(components=4)
            self.writing_process.stdin.write(bytes)

        self.close_video_pipe()

        log.info(f'Finished writing "{name}" in {time.time() - t:.2f} s')

    def open_video_pipe(self, file_path: str) -> None:
        stem, ext = os.path.splitext(file_path)
        self.final_file_path = file_path
        self.temp_file_path = stem + '_temp' + ext

        command = [
            Config.get.ffmpeg_bin,
            '-y',  # overwrite output file if it exists
            '-f', 'rawvideo',
            '-s', f'{Config.get.pixel_width}x{Config.get.pixel_height}',  # size of one frame
            '-pix_fmt', 'rgba',
            '-r', str(Config.get.fps),  # frames per second
            '-i', '-',  # The input comes from a pipe
            '-vf', 'vflip',
            '-an',  # Tells FFMPEG not to expect any audio
            '-loglevel', 'error',
        ]

        if ext == ".mov":
            # This is if the background of the exported
            # video should be transparent.
            command += [
                '-vcodec', 'qtrle',
            ]
        else:
            command += [
                '-vcodec', 'libx264',
                '-pix_fmt', 'yuv420p',
            ]

        command += [self.temp_file_path]
        self.writing_process = sp.Popen(command, stdin=sp.PIPE)

    def close_video_pipe(self) -> None:
        self.writing_process.stdin.close()
        self.writing_process.wait()
        self.writing_process.terminate()
        shutil.move(self.temp_file_path, self.final_file_path)

    @staticmethod
    def writes(anim: TimelineAnim, file_path: str) -> None:
        FileWriter(anim).write_all(file_path)
