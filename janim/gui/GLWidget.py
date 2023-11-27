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
    # 默认帧率 60
    # delay_ms 表示两帧之间间隔的毫秒数
    frame_rate = 60
    delay_ms = 1000 / frame_rate

    # pan_sensitivity 表示转动视野的灵敏度
    # move_sensitivity 表示移动视野的灵敏度
    pan_sensitivity = 0.3
    move_sensitivity = 0.02

    def __init__(
        self, 
        scene: Scene, 
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.scene = scene

        # 与常规的（wait、play 会因为 emit_frame 而自动调用 update）不同：
        # 鼠标对视野的移动、转动、滚轮、'R'键重置等操作
        # 需要将下面这个 updateFlag 设置为 True 以标记需要进行 update
        #
        # 主要作用是在 embed 模式中，在用户没有进行输入的情况下
        # 停止屏幕内容的刷新，以提升性能
        self.updateFlag = False

        # 定时器，用于定时调用绘制
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.onTimerTimeout)
        self.timer.start(self.delay_ms)

        # 窗口属性
        self.setMinimumSize(100, 100)
        self.setWindowTitle('JAnim Graphics')

        # 用于窗口额外内容的绘制，如外围边界部分条纹线
        self.window_renderer = WindowRenderer()

    def onTimerTimeout(self) -> None:
        # 在有 update 需求时进行调用，具体参考对 self.updateFlag 的描述
        if self.updateFlag:
            self.updateFlag = False
            self.update()

    #region OpenGL

    def initializeGL(self) -> None:
        # 设置清屏背景颜色
        glClearColor(*hex_to_rgb(self.scene.background_color), 1.0)
        
        # 颜色混合
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.window_renderer.init()

    def paintGL(self) -> None:
        # 正在 skipping 时不进行渲染，以避免不必要的时间浪费
        try:
            if self.scene.check_skipping():
                return
        except EndSceneEarlyException:
            pass

        try:
            # 对场景进行渲染
            self.scene.render()

            # 计算中间空白区域
            wnd_shape = self.scene.camera.wnd_shape
            camera_shape = (1920, 1080)
            min_f = min(wnd_shape[0] / camera_shape[0], wnd_shape[1] / camera_shape[1])
            xy_buff = (
                0.5 - (camera_shape[0] * min_f / wnd_shape[0]) / 2,
                0.5 - (camera_shape[1] * min_f / wnd_shape[1]) / 2
            )

            # 根据上面的数据，绘制外围边界部分的条纹线
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

        # 记录鼠标按下的位置，方便 MoveEvent 中计算移动量
        if event.button() == Qt.MouseButton.MiddleButton:
            self.mbutton_pos = event.position()
        elif event.button() == Qt.MouseButton.RightButton:
            self.rbutton_pos = event.position()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)

        # 移动视野
        if event.buttons() & Qt.MouseButton.MiddleButton:
            pos = event.position()
            d_pos = pos - self.mbutton_pos
            x, y = d_pos.toTuple()

            camera = self.scene.camera

            # 移动 camera，其中 camera.get_vertical_dist() / FRAME_HEIGHT 的因素，
            # 使得移动速度是相对摄像机大小而言的
            camera.shift(
                self.move_sensitivity * camera.get_vertical_dist() / FRAME_HEIGHT * (
                    - normalize(camera.get_horizontal_vect()) * x
                    + normalize(camera.get_vertical_vect()) * y
                )
            )

            self.mbutton_pos = pos
            self.updateFlag = True

        # 转动视野
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

        # 重置摄像机位置
        if event.key() == Qt.Key.Key_R:
            self.scene.camera.reset()
            self.updateFlag = True

    def wheelEvent(self, event: QWheelEvent) -> None:
        super().wheelEvent(event)
        delta = event.angleDelta().y()
        
        # 缩放摄像机
        self.scene.camera.scale(0.96 if delta > 0 else 1 / 0.96)
        self.updateFlag = True

    #endregion
