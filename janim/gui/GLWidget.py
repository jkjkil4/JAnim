from typing import Optional
import numpy as np
import traceback

from PySide6.QtCore import Qt
from PySide6.QtCore import QTimer
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QWidget
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtOpenGL import *
from OpenGL.GL import *

from janim.constants import *
from janim.scene import Scene
from janim.items.dot_cloud import DotCloud
from utils.space_ops import normalize


class GLWidget(QOpenGLWidget):
    frame_rate = 60
    pan_sensitivity = 0.3
    move_sensitivity = 0.02
    wheel_step = 0.5

    def __init__(
        self, 
        scene: Scene, 
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.scene = scene

        # 基本属性
        self.setMinimumSize(100, 100)

        # 定时器，用于定时调用绘制
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)  # 使定时更准确
        self.timer.timeout.connect(self.update)             # 达到定时后调用 `update`
        self.timer.start(1000 / self.frame_rate)

        # TODO: 删除
        self.setWindowTitle('JAnim')

    #region OpenGL

    def initializeGL(self) -> None:
        glClearColor(0.2, 0.3, 0.3, 1.0)
        # glClearColor(0, 0, 0, 1)    # 将背景色设置为黑色
        # glEnable(GL_MULTISAMPLE)    # 抗锯齿
        # glEnable(GL_DEPTH_TEST)
        
        # 颜色混合
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # self.tex1 = QOpenGLTexture(QOpenGLTexture.Target.Target2D)
        # self.tex1.create()
        # self.tex1.setData(QImage('assets/container.jpg').mirrored(False, True))
        # self.tex1.setMinMagFilters(QOpenGLTexture.Filter.Linear, QOpenGLTexture.Filter.Linear)
        # self.tex1.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)

        # self.tex2 = QOpenGLTexture(QOpenGLTexture.Target.Target2D)
        # self.tex2.create()
        # self.tex2.setData(QImage('assets/awesomeface.png').mirrored(False, True))
        # self.tex2.setMinMagFilters(QOpenGLTexture.Filter.Linear, QOpenGLTexture.Filter.Linear)
        # self.tex2.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
        
        # glUniform1i(self.shader.uniformLocation('texture1'), 0)
        # glUniform1i(self.shader.uniformLocation('texture2'), 1)

    def paintGL(self) -> None:
        try:
            self.scene.render()
        except:
            traceback.print_exc()
            exit(1)

        # glActiveTexture(GL_TEXTURE0)
        # self.tex1.bind()
        # glActiveTexture(GL_TEXTURE1)
        # self.tex2.bind()

        # self.shader.bind()

    def resizeGL(self, w: int, h: int) -> None:
        super().resizeGL(w, h)
        glViewport(0, 0, w, h)
        self.scene.camera.wnd_shape = (w, h)

    #endregion

    #region 用户操作

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)

        if event.button() == Qt.MouseButton.MiddleButton:
            self.mbutton_pos = event.position()
        elif event.button() == Qt.MouseButton.RightButton:
            self.rbutton_pos = event.position()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)

        if event.buttons() & Qt.MouseButton.MiddleButton:
            pos = event.position()
            d_pos = pos - self.mbutton_pos
            x, y = d_pos.toTuple()

            camera = self.scene.camera
            camera.shift(
                self.move_sensitivity * camera.get_vertical_dist() / FRAME_HEIGHT * (
                    - normalize(camera.get_horizontal_vect()) * x
                    + normalize(camera.get_vertical_vect()) * y
                )
            )

            self.mbutton_pos = pos

        if event.buttons() & Qt.MouseButton.RightButton:
            pos = event.position()
            d_pos = pos - self.rbutton_pos
            x, y = d_pos.toTuple()

            camera = self.scene.camera
            camera.rotate(-self.pan_sensitivity * x * DEGREES, OUT)
            camera.rotate(-self.pan_sensitivity * y * DEGREES, camera.get_horizontal_vect())
            
            self.rbutton_pos = pos

    def wheelEvent(self, event: QWheelEvent) -> None:
        super().wheelEvent(event)
        delta = event.angleDelta().y()
        
        self.scene.camera.scale(0.98 if delta > 0 else 1 / 0.98)
    
    #endregion
