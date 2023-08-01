import traceback
import sys, os
import subprocess as sp
import shutil

from OpenGL.GL import *

from PySide6.QtGui import QOpenGLContext, QOffscreenSurface
from PySide6.QtOpenGL import QOpenGLFramebufferObject

from janim.constants import *
from janim.scene.scene import Scene, EndSceneEarlyException
from janim.utils.color import hex_to_rgb
from janim.utils.file_ops import guarantee_existence, open_file
from janim.config import get_cli, get_configuration
from janim.logger import log

class Frame:
    def __init__(self, scene: Scene) -> None:
        self.scene = scene

        self.surface = QOffscreenSurface()
        self.surface.create()

        self.context = QOpenGLContext()
        self.context.create()
        self.context.makeCurrent(self.surface)

        self.fbo = QOpenGLFramebufferObject(
            *self.scene.camera.wnd_shape,
            QOpenGLFramebufferObject.Attachment.Depth,
            internalFormat=GL_RGB
        )

        output_path = guarantee_existence(os.path.join(get_configuration()['directories']['output'], 'videos'))
        output_filepath = os.path.join(output_path, f'{self.scene.__class__.__name__}.mp4')
        self.open_movie_pipe(output_filepath)

        glViewport(0, 0, *self.scene.camera.wnd_shape)
        glClearColor(*hex_to_rgb(self.scene.background_color), 1.0)

        # 颜色混合
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def emit_frame(self) -> None:
        try:
            if self.scene.check_skipping():
                return
        except EndSceneEarlyException:
            pass
        
        self.fbo.bind()

        glClear(GL_COLOR_BUFFER_BIT)
        try:
            self.scene.render()
        except:
            traceback.print_exc()
            sys.exit(1)

        raw_bytes = glReadPixels(0, 0, *self.scene.camera.wnd_shape, GL_RGB, GL_UNSIGNED_BYTE)
        self.writing_process.stdin.write(raw_bytes)
        
        self.fbo.release()
        
    def finish(self) -> None:
        self.close_movie_pipe()
    
    def open_movie_pipe(self, file_path: str):  # TODO: optimize
        stem, ext = os.path.splitext(file_path)
        self.temp_file_path = stem + "_temp" + ext
        self.final_file_path = file_path

        # TODO: frame_rate
        fps = 60
        width, height = self.scene.camera.wnd_shape

        command = [
            FFMPEG_BIN,
            '-y',  # overwrite output file if it exists
            '-f', 'rawvideo',
            '-s', f'{width}x{height}',  # size of one frame
            '-pix_fmt', 'rgb24',
            '-r', str(fps),  # frames per second
            '-i', '-',  # The input comes from a pipe
            '-vf', 'vflip',
            '-an',  # Tells FFMPEG not to expect any audio
            '-loglevel', 'error',
        ]
        # TODO: movie_file_extension
        # if self.movie_file_extension == ".mov":
        #     # This is if the background of the exported
        #     # video should be transparent.
        #     command += [
        #         '-vcodec', 'qtrle',
        #     ]
        # elif self.movie_file_extension == ".gif":
        #     command += []
        # else:
        command += [
            '-vcodec', 'libx264',
            '-pix_fmt', 'yuv420p',
        ]

        command += [self.temp_file_path]
        self.writing_process = sp.Popen(command, stdin=sp.PIPE)

    def close_movie_pipe(self) -> None:
        self.writing_process.stdin.close()
        self.writing_process.wait()
        self.writing_process.terminate()
        shutil.move(self.temp_file_path, self.final_file_path)

        log.info(f"File ready at {self.final_file_path}")

        if get_cli().open:
            open_file(self.final_file_path)
    

        
