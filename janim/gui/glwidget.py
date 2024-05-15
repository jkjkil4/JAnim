
import moderngl as mgl
from PySide6.QtCore import Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from janim.anims.timeline import TimelineAnim


class GLWidget(QOpenGLWidget):
    '''
    窗口中央的渲染界面
    '''
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
        self.ctx.blend_func = (
            mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA,
            mgl.ONE, mgl.ONE
        )
        self.ctx.blend_equation = mgl.FUNC_ADD, mgl.MAX

        self.qfuncs = self.context().functions()

        self.ctx.clear(*self.anim.cfg.background_color.rgb)

    def paintGL(self) -> None:
        self.qfuncs.glClear(0x00004000 | 0x00000100)    # GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT
        self.anim.render_all(self.ctx)
        self.rendered.emit()
