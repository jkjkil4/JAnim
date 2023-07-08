from typing import Optional
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPaintEvent, QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QWidget
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtOpenGL import *
from OpenGL.GL import *

from janim.constants import *
from janim.scene import Scene
from janim.items.dot_cloud import DotCloud
from janim.utils.math_functions import normalize, get_unit_normal

import time

class GLWidget(QOpenGLWidget):
    frame_rate = DEFAULT_FRAME_RATE
    pan_sensitivity = 0.3
    move_sensitivity = 0.02
    wheel_step = 0.5

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # 基本属性
        # self.frameRate = 30
        self.setMinimumSize(100, 100)

        # 定时器，用于定时调用绘制，详见 `paintEvent`
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)  # 使定时更准确
        self.timer.setSingleShot(True)                      # 由于每次触发时间不确定，因此是单次触发，每次触发后另行控制
        self.timer.timeout.connect(self.update)             # 达到定时后调用 `update`

        # 场景
        self.scene: Scene = None

        # 仅测试
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.scene = Scene()
        d1 = DotCloud([LEFT * 6 + RIGHT * 0.5 * i for i in range(25)])\
            .set_color([RED, GREEN, BLUE])\
            .set_radius([0.1, 0.05, 0.1, 0.05])
        d2 = DotCloud([LEFT, RIGHT, UP, DOWN])\
            .next_to(d1, DOWN, aligned_edge=RIGHT)\
            .set_radius(0.1)
        self.scene.add(d1, d2)
        self.i = 0

    #region OpenGL

    def initializeGL(self) -> None:
        glClearColor(0, 0, 0, 1)    # 将背景色设置为黑色
        glEnable(GL_MULTISAMPLE)    # 抗锯齿

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
        self.scene.render()

        # glActiveTexture(GL_TEXTURE0)
        # self.tex1.bind()
        # glActiveTexture(GL_TEXTURE1)
        # self.tex2.bind()

        # self.shader.bind()

    def resizeGL(self, w: int, h: int) -> None:
        super().resizeGL(w, h)
        glViewport(0, 0, w, h)
        self.scene.camera.wnd_shape = (w, h)

    def paintEvent(self, e: QPaintEvent) -> None:
        '''
        重载 `paintEvent`，用于计算 `paintGL` 用时，
        并将计划用时（默认 1 / 30 s）减去 `paintGL` 用时后，作为定时器的触发时间，
        这样就可以做到每次间隔计划用时调用绘制

        如果 `paintGL` 用时超过计划用时，则立即调用下一次 update
        
        注：这里的 update 不会对物件数据造成变动，仅用于定时更新画面
        '''
        start = time.perf_counter()
        super().paintEvent(e)
        elapsed = time.perf_counter() - start
        plan = 1 / self.frame_rate
        if elapsed < plan:
            self.timer.start((plan - elapsed) * 1000)
        else:
            self.update()

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
                - normalize(camera.get_horizontal_vect()) * x * self.move_sensitivity
                + normalize(camera.get_vertical_vect()) * y * self.move_sensitivity
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
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)
        
        if event.key() == Qt.Key.Key_R:
            self.scene.camera.reset()
    
    #endregion
