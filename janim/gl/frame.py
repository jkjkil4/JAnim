import traceback
import sys, os
import subprocess as sp
import shutil

from OpenGL.GL import *

from PySide6.QtGui import QOpenGLContext, QOffscreenSurface
from PySide6.QtOpenGL import QOpenGLFramebufferObject

from janim.constants import *
from janim.scene.scene import Scene, EndSceneEarlyException
from janim.gl.texture import Texture
from janim.utils.color import hex_to_rgb
from janim.utils.file_ops import guarantee_existence, open_file
from janim.config import get_cli, get_configuration
from janim.logger import log

class Frame:
    '''
    用于将动画内容输出到文件
    '''
    def __init__(self, scene: Scene) -> None:
        self.scene = scene

        # 配置离屏渲染
        self.surface = QOffscreenSurface()
        self.surface.create()

        self.context = QOpenGLContext()
        self.context.create()
        self.context.makeCurrent(self.surface)

        cli = get_cli()
        self.color_space = GL_RGBA if cli.transparent else GL_RGB
        self.ffmpeg_color_space = 'rgba' if cli.transparent else 'rgb24'

        self.fbo = QOpenGLFramebufferObject(
            *self.scene.camera.wnd_shape,
            QOpenGLFramebufferObject.Attachment.Depth,
            internalFormat=self.color_space
        )

        output_path = guarantee_existence(get_configuration()['directories']['output'])
        output_filepath_wo_ext = os.path.join(output_path, self.scene.__class__.__name__)
        self.open_movie_pipe(output_filepath_wo_ext)

        glClearColor(*hex_to_rgb(self.scene.background_color), 0.0 if cli.transparent else 1.0)

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
            glViewport(0, 0, *self.scene.camera.wnd_shape)
            self.scene.render()
        except:
            traceback.print_exc()
            sys.exit(1)

        # 获取图像数据并传递给 ffmpeg
        raw_bytes = glReadPixels(0, 0, *self.scene.camera.wnd_shape, self.color_space, GL_UNSIGNED_BYTE)
        self.writing_process.stdin.write(raw_bytes)
        
        self.fbo.release()
        
    def finish(self) -> None:
        Texture.release_all()
        self.close_movie_pipe()
    
    def open_movie_pipe(self, file_path: str):
        '''打开与 ffmpeg 的数据流'''

        cli = get_cli()
        conf = get_configuration()
        width, height = self.scene.camera.wnd_shape

        command = [
            FFMPEG_BIN,
            '-y',  # overwrite output file if it exists
            '-f', 'rawvideo',
            '-s', f'{width}x{height}',  # size of one frame
            '-pix_fmt', self.ffmpeg_color_space,
            '-r', str(self.scene.frame_rate),  # frames per second
            '-i', '-',  # The input comes from a pipe
            '-vf', 'vflip',
            '-an',  # Tells FFMPEG not to expect any audio
            '-loglevel', 'error',
        ]

        vcodec = cli.vcodec

        if cli.transparent:
            vcodec = vcodec or conf['output']['mov_vcodec']
            ext = '.mov'
        elif cli.gif:
            ext = '.gif'
        else:
            vcodec = vcodec or conf['output']['mp4_vcodec']
            ext = '.mp4'

        if vcodec:
            command += ['-vcodec', vcodec]

        self.temp_file_path = file_path + "_temp" + ext
        self.final_file_path = file_path + ext

        command += [self.temp_file_path]

        log.info(f'导出参数    frame_rate: {self.scene.frame_rate}, vcodec: "{vcodec}"')

        self.writing_process = sp.Popen(command, stdin=sp.PIPE)

    def close_movie_pipe(self) -> None:
        '''关闭与 ffmpeg 的数据流，并进行最终处理'''
        
        self.writing_process.stdin.close()
        self.writing_process.wait()
        self.writing_process.terminate()
        shutil.move(self.temp_file_path, self.final_file_path)

        log.info(f"File ready at {self.final_file_path}")

        if get_cli().open:
            open_file(self.final_file_path)
            
