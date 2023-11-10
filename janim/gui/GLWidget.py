import sys
import traceback

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QMouseEvent, QKeyEvent, QWheelEvent
from PySide6.QtWidgets import QWidget
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtOpenGL import *
from OpenGL.GL import *

from janim.constants import *
from janim.scene.scene import Scene, EndSceneEarlyException
from janim.gl.render import WindowRenderer
from janim.utils.space_ops import normalize
from janim.utils.color import hex_to_rgb

from janim.logger import log

class GLWidget(QOpenGLWidget):
    frame_rate = 60
    delay_ms = 1000 / frame_rate

    pan_sensitivity = 0.3
    move_sensitivity = 0.02

    def __init__(
        self, 
        scene: Scene, 
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.scene = scene

        self.updateFlag = False

        # 基本属性
        self.setMinimumSize(100, 100)

        # 定时器，用于定时调用绘制
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.onTimerTimeout)
        self.timer.start(self.delay_ms)

        self.setWindowTitle('JAnim Graphics')

        self.window_renderer = WindowRenderer()

    def onTimerTimeout(self) -> None:
        if self.updateFlag:
            self.updateFlag = False
            self.update()

    #region OpenGL

    def initializeGL(self) -> None:
        glClearColor(*hex_to_rgb(self.scene.background_color), 1.0)
        
        # 颜色混合
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.window_renderer.init()

    def paintGL(self) -> None:
        try:
            if self.scene.check_skipping():
                return
        except EndSceneEarlyException:
            pass

        try:
            self.scene.render()

            wnd_shape = self.scene.camera.wnd_shape
            camera_shape = (1920, 1080)
            min_f = min(wnd_shape[0] / camera_shape[0], wnd_shape[1] / camera_shape[1])
            xy_buff = (
                0.5 - (camera_shape[0] * min_f / wnd_shape[0]) / 2,
                0.5 - (camera_shape[1] * min_f / wnd_shape[1]) / 2
            )

            self.window_renderer.render(wnd_shape, xy_buff)
        except:
            traceback.print_exc()
            sys.exit(1)

    def resizeGL(self, w: int, h: int) -> None:
        super().resizeGL(w, h)
        glViewport(0, 0, w, h)
        self.scene.camera.wnd_shape = (w, h)

    #endregion

    #region Events

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
            self.updateFlag = True

        if event.buttons() & Qt.MouseButton.RightButton:
            pos = event.position()
            d_pos = pos - self.rbutton_pos
            x, y = d_pos.toTuple()

            camera = self.scene.camera
            camera.rotate(-self.pan_sensitivity * x * DEGREES, OUT)
            camera.rotate(-self.pan_sensitivity * y * DEGREES, camera.get_horizontal_vect())
            
            self.rbutton_pos = pos
            self.updateFlag = True

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        super().keyReleaseEvent(event)

        if event.key() == Qt.Key.Key_R:
            self.scene.camera.reset()
            self.updateFlag = True

    def wheelEvent(self, event: QWheelEvent) -> None:
        super().wheelEvent(event)
        delta = event.angleDelta().y()
        
        self.scene.camera.scale(0.96 if delta > 0 else 1 / 0.96)
        self.updateFlag = True

    #endregion
