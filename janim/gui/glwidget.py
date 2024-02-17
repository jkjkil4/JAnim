
import moderngl as mgl
from PySide6.QtCore import Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from janim.anims.timeline import TimelineAnim
from janim.utils.config import Config


class GLWidget(QOpenGLWidget):
    rendered = Signal()

    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.anim = anim

    def set_time(self, time: float) -> None:
        self.anim.anim_on(time)
        self.update()

    def initializeGL(self) -> None:
        self.ctx = mgl.create_context()
        self.ctx.enable(mgl.BLEND)

        self.ctx.clear(*Config.get.background_color.rgb)

    def paintGL(self) -> None:
        self.anim.render_all(self.ctx)
        self.rendered.emit()
