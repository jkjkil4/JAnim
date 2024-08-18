
import moderngl as mgl
from PySide6.QtCore import QPointF, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from janim.anims.timeline import TimelineAnim


class GLWidget(QOpenGLWidget):
    '''
    窗口中央的渲染界面
    '''
    rendered = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.needs_update_clear_color = False

    def set_anim(self, anim: TimelineAnim) -> None:
        self.anim = anim
        self.update_clear_color()
        self.update()

    def set_time(self, time: float) -> None:
        self.anim.anim_on(time)
        self.update()

    def map_to_gl2d(self, point: QPointF) -> tuple[float, float]:
        x, y = point.toTuple()
        w, h = self.size().toTuple()
        glx = x / w * 2 - 1
        gly = y / h * -2 + 1
        return glx, gly

    def map_to_widget(self, x: float, y: float) -> QPointF:
        w, h = self.size().toTuple()
        xx = (x + 1) / 2 * w
        yy = (-y + 1) / 2 * h
        return QPointF(xx, yy)

    def initializeGL(self) -> None:
        self.ctx = mgl.create_context()
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = (
            mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA,
            mgl.ONE, mgl.ONE
        )
        self.ctx.blend_equation = mgl.FUNC_ADD, mgl.MAX

        self.qfuncs = self.context().functions()
        self.update_clear_color()

    def update_clear_color(self) -> None:
        self.needs_update_clear_color = True

    def paintGL(self) -> None:
        if self.needs_update_clear_color:
            self.qfuncs.glClearColor(*self.anim.cfg.background_color.rgb, 0.)
            self.needs_update_clear_color = False
        self.qfuncs.glClear(0x00004000 | 0x00000100)    # GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT
        self.anim.render_all(self.ctx)
        self.rendered.emit()
