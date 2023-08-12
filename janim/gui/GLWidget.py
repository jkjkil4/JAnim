from typing import Optional
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
from janim.utils.space_ops import normalize
from janim.utils.color import hex_to_rgb

from janim.logger import log


class GLWidget(QOpenGLWidget):
    frame_rate = 60

    pan_sensitivity = 0.3
    move_sensitivity = 0.02

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
        self.timer.timeout.connect(self.onTimerTimeout)
        self.timer.start(1000 / self.frame_rate)

        self.setWindowTitle('JAnim Graphics')

    def onTimerTimeout(self) -> None:
        self.update()

    #region OpenGL

    def initializeGL(self) -> None:
        glClearColor(*hex_to_rgb(self.scene.background_color), 1.0)
        
        # 颜色混合
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def paintGL(self) -> None:
        try:
            if self.scene.check_skipping():
                return
        except EndSceneEarlyException:
            pass

        try:
            self.scene.render()
        except:
            traceback.print_exc()
            sys.exit(1)

    def resizeGL(self, w: int, h: int) -> None:
        super().resizeGL(w, h)
        glViewport(0, 0, w, h)
        self.scene.camera.wnd_shape = (w, h)

    #endregion

    #region socket

    def enableSocket(self) -> None:
        from PySide6.QtNetwork import QUdpSocket

        self.socket = QUdpSocket()
        self.socket.bind()

        self.stored_states = 0

        log.info(f'调试端口已在 {self.socket.localPort()} 开启')

        self.socket.readyRead.connect(self.onReadyRead)

    def onReadyRead(self) -> None:
        import json

        while self.socket.hasPendingDatagrams():
            datagram = self.socket.receiveDatagram()
            try:
                tree = json.loads(datagram.data().toStdString())
                assert('janim' in tree)
                
                janim = tree['janim']
                type = janim['type']
                if type == 'exec_code':
                    self.scene.save_state(f'_d_{self.stored_states}')
                    self.stored_states += 1

                    lines = janim['data'].splitlines()
                    indent = 0
                    for line in lines:
                        line_indent = 0
                        for char in line:
                            if char not in '\t ':
                                break
                            line_indent += 1

                        indent = line_indent if indent == 0 else min(indent, line_indent)

                    self.scene.execute('\n'.join(line[indent:] for line in lines))

                elif type == 'undo_code':
                    if self.stored_states > 0:
                        self.stored_states -= 1
                        self.scene.restore(f'_d_{self.stored_states}')
                        log.info(f'已撤销代码')
                    else:
                        log.info('已回到初始状态，无法再撤销')
            except:
                traceback.print_exc()
                pass

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

        if event.buttons() & Qt.MouseButton.RightButton:
            pos = event.position()
            d_pos = pos - self.rbutton_pos
            x, y = d_pos.toTuple()

            camera = self.scene.camera
            camera.rotate(-self.pan_sensitivity * x * DEGREES, OUT)
            camera.rotate(-self.pan_sensitivity * y * DEGREES, camera.get_horizontal_vect())
            
            self.rbutton_pos = pos

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        super().keyReleaseEvent(event)

        if event.key() == Qt.Key.Key_R:
            self.scene.camera.reset()

    def wheelEvent(self, event: QWheelEvent) -> None:
        super().wheelEvent(event)
        delta = event.angleDelta().y()
        
        self.scene.camera.scale(0.96 if delta > 0 else 1 / 0.96)

    #endregion
