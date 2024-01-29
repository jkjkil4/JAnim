
import traceback
from typing import TYPE_CHECKING

import moderngl as mgl
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import QEvent, QTimer, QSize

from janim.anims.animation import Animation
from janim.render.base import Renderer, RenderData

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

MAX_RESIZE_RATE = 20
MIN_RESIZE_DURATION = 1000 // MAX_RESIZE_RATE


class GLWidget(QOpenGLWidget):
    def __init__(self, parent: 'AnimViewer') -> None:
        super().__init__(parent)
        self.anim = parent.anim

        self._progress: float | None = None

        self.old_size = QSize()
        self.target_size = QSize()

        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.on_resize_timeout)

    def set_progress(self, progress: float) -> None:
        self._progress = progress

        token = Animation.global_t_ctx.set(progress)
        self.anim.anim_on(progress)
        Animation.global_t_ctx.reset(token)

        self.update()

    def on_resize_timeout(self) -> None:
        QApplication.instance().postEvent(
            self,
            QResizeEvent(self.target_size, self.old_size)
        )
        self.old_size = self.target_size

    def initializeGL(self) -> None:
        self.ctx = mgl.create_context()

    def paintGL(self) -> None:
        if self._progress is None:
            return

        render_token = Renderer.data_ctx.set(RenderData(self.ctx))
        global_t_token = Animation.global_t_ctx.set(self._progress)

        try:
            self.anim.render()
        except Exception:
            traceback.print_exc()

        Animation.global_t_ctx.reset(global_t_token)
        Renderer.data_ctx.reset(render_token)

    def event(self, e: QEvent) -> bool:
        if e.type() == QEvent.Type.Resize and e.size() != self.target_size:
            self.target_size = e.size()
            self.resize_timer.start(MIN_RESIZE_DURATION)
            e.ignore()
            return True

        return super().event(e)
