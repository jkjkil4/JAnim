from typing import Optional
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QMatrix4x4, QPaintEvent
from PySide6.QtWidgets import QWidget
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtOpenGL import *
from OpenGL.GL import *

from constants import *

import time

class GLWidget(QOpenGLWidget):
    def __init__(self, parent: Optional[QWidget]=None) -> None:
        super().__init__(parent)

        self.frameRate = 30

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.update)

    def initializeGL(self) -> None:
        glClearColor(0.2, 0.3, 0.3, 1.0)
        glEnable(GL_MULTISAMPLE)

        self.shader = QOpenGLShaderProgram()
        self.shader.addShaderFromSourceFile(QOpenGLShader.ShaderTypeBit.Vertex, 'shaders/tex.vert')
        self.shader.addShaderFromSourceFile(QOpenGLShader.ShaderTypeBit.Fragment, 'shaders/tex.frag')
        self.shader.link()
        self.shader.bind()
        
        vertices = np.array([
            # positions       # texture coords
            0.5,  0.5, 0.0,   1.0, 1.0, # top right
            0.5, -0.5, 0.0,   1.0, 0.0, # bottom right
           -0.5, -0.5, 0.0,   0.0, 0.0, # bottom left
           -0.5,  0.5, 0.0,   0.0, 1.0  # top left 
        ]).astype(np.float32)

        self.indices = np.array([
            0, 1, 3,
            1, 2, 3
        ]).astype(np.uint)

        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)

        glBindVertexArray(self.vao)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, len(vertices) * FLOAT_SIZE, vertices, GL_STATIC_DRAW)

        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * FLOAT_SIZE, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * FLOAT_SIZE, ctypes.c_void_p(3 * FLOAT_SIZE))
        glEnableVertexAttribArray(1)

        glBindVertexArray(0)

        self.tex1 = QOpenGLTexture(QOpenGLTexture.Target.Target2D)
        self.tex1.create()
        self.tex1.setData(QImage('assets/container.jpg').mirrored(False, True))
        self.tex1.setMinMagFilters(QOpenGLTexture.Filter.Linear, QOpenGLTexture.Filter.Linear)
        self.tex1.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)

        self.tex2 = QOpenGLTexture(QOpenGLTexture.Target.Target2D)
        self.tex2.create()
        self.tex2.setData(QImage('assets/awesomeface.png').mirrored(False, True))
        self.tex2.setMinMagFilters(QOpenGLTexture.Filter.Linear, QOpenGLTexture.Filter.Linear)
        self.tex2.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
        
        glUniform1i(self.shader.uniformLocation('texture1'), 0)
        glUniform1i(self.shader.uniformLocation('texture2'), 1)

    def paintGL(self) -> None:
        glActiveTexture(GL_TEXTURE0)
        self.tex1.bind()
        glActiveTexture(GL_TEXTURE1)
        self.tex2.bind()

        self.shader.bind()

        model = QMatrix4x4(IDEN_MAT)
        model.rotate(60 * (time.time() % 6), 1, 0, 0)
        self.shader.setUniformValue(self.shader.uniformLocation('model'), model)

        view = QMatrix4x4(IDEN_MAT)
        view.translate(0, 0, -3)
        self.shader.setUniformValue(self.shader.uniformLocation('view'), view)

        projection = QMatrix4x4(IDEN_MAT)
        projection.perspective(45, self.width() / self.height(), 0.1, 100)
        self.shader.setUniformValue(self.shader.uniformLocation('projection'), projection)

        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, self.indices)
        glBindVertexArray(0)

    def resizeGL(self, w: int, h: int) -> None:
        super().resizeGL(w, h)
        glViewport(0, 0, w, h)

    def paintEvent(self, e: QPaintEvent) -> None:
        start = time.perf_counter()
        super().paintEvent(e)
        elapsed = time.perf_counter() - start
        plan = 1 / self.frameRate
        if elapsed < plan:
            self.timer.start((plan - elapsed) * 1000)
        else:
            self.update()

