from PySide6.QtGui import QMatrix4x4
from PySide6.QtOpenGL import *
from OpenGL.GL import *

from janim.constants import *

class RenderData:
    def __init__(self, camera_matrix: QMatrix4x4, wnd_mul_proj_matrix: QMatrix4x4) -> None:
        self.view_matrix = camera_matrix
        self.wnd_mul_proj_matrix = wnd_mul_proj_matrix

class Renderer:
    def __init__(self) -> None:
        self.initialized = False
        self.needs_update = True

    def prepare(self, item) -> None:
        if not self.initialized:
            self.init()
            self.initialized = True
        
        if self.needs_update:
            self.update(item)
            self.needs_update = False

    def init(self) -> None:
        pass

    def update(self, item) -> None:
        pass

    def pre_render(self, item, data: RenderData) -> None:
        pass
    
    def render(self, item, data: RenderData) -> None:
        pass

    @staticmethod
    def setMat4(shader: QOpenGLShaderProgram, name: str, mat: QMatrix4x4) -> None:
        shader.setUniformValue(shader.uniformLocation(name), mat)

class DotCloudRenderer(Renderer):
    def init(self) -> None:
        self.shader = QOpenGLShaderProgram()
        self.shader.addShaderFromSourceFile(QOpenGLShader.ShaderTypeBit.Vertex, 'shaders/dotcloud.vert')
        self.shader.addShaderFromSourceFile(QOpenGLShader.ShaderTypeBit.Geometry, 'shaders/dotcloud.geom')
        self.shader.addShaderFromSourceFile(QOpenGLShader.ShaderTypeBit.Fragment, 'shaders/dotcloud.frag')
        if not self.shader.link():
            print('Failed to link DotCloudRenderData.shader')
            exit(1)
        self.shader.bind()

        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
    
    def update(self, item) -> None:
        glBindVertexArray(self.vao)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, item.points.size * FLOAT_SIZE, item.points, GL_STATIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * FLOAT_SIZE, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        glBindVertexArray(0)
    
    def render(self, item, data: RenderData) -> None:
        self.shader.bind()

        self.setMat4(self.shader, 'view_matrix', data.view_matrix)
        self.setMat4(self.shader, 'wnd_mul_proj_matrix', data.wnd_mul_proj_matrix)

        glBindVertexArray(self.vao)
        glDrawArrays(GL_POINTS, 0, len(item.points))
        glBindVertexArray(0)

