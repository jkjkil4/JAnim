
import moderngl as mgl
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from janim.anims.animation import Animation
from janim.anims.timeline import TimelineAnim

MAX_RESIZE_RATE = 20
MIN_RESIZE_DURATION = 1000 // MAX_RESIZE_RATE


class GLWidget(QOpenGLWidget):
    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.anim = anim

    def set_time(self, time: float) -> None:
        token = Animation.global_t_ctx.set(time)
        try:
            self.anim.anim_on(time)
        finally:
            Animation.global_t_ctx.reset(token)

        self.update()

    def initializeGL(self) -> None:
        self.ctx = mgl.create_context()
        self.ctx.enable(mgl.BLEND)

    def paintGL(self) -> None:
        self.anim.render_all(self.ctx)
