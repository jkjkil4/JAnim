
from PySide6.QtCore import QPointF, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from janim.anims.timeline import BuiltTimeline
from janim.logger import log
from janim.camera.camera import Camera
from janim.render.base import create_context
from janim.render.framebuffer import FRAME_BUFFER_BINDING, register_qt_glwidget


class GLWidget(QOpenGLWidget):
    """
    窗口中央的渲染界面
    """
    rendered = Signal()
    error_occurred = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.needs_update_clear_color = False
        self.inject_camera: Camera | None = None

    def set_built(self, built: BuiltTimeline) -> None:
        self.built = built
        self.update_clear_color()
        self.update()

    def set_time(self, time: float) -> None:
        self.global_t = time
        self.update()

    def map_to_gl2d(self, point: QPointF) -> tuple[float, float]:
        x, y = point.toTuple()
        w, h = self.size().toTuple()
        glx = x / w * 2 - 1
        gly = y / h * -2 + 1
        return glx, gly

    def map_from_gl2d(self, x: float, y: float) -> QPointF:
        w, h = self.size().toTuple()
        xx = (x + 1) / 2 * w
        yy = (-y + 1) / 2 * h
        return QPointF(xx, yy)

    def map_to_glx(self, point: QPointF) -> float:
        return point.x() / self.width() * 2 - 1

    def map_to_gly(self, point: QPointF) -> float:
        return point.y() / self.height() * -2 + 1

    def map_from_glx(self, x: float) -> float:
        return (x + 1) / 2 * self.width()

    def map_from_gly(self, y: float) -> float:
        return (-y + 1) / 2 * self.height()

    def initializeGL(self) -> None:
        log.debug('Initializing OpenGL context for GLWidget ..')
        self.ctx = create_context()
        log.debug('Obtained OpenGL context of GLWidget')

        self.qfuncs = self.context().functions()
        self.update_clear_color()

        register_qt_glwidget(self)

        # null_texture 目的是避免还没有 framebuffer 绑定至纹理单元时，在渲染的时候出现警告
        self.null_texture = self.ctx.texture((1, 1), 1)

    def update_clear_color(self) -> None:
        self.needs_update_clear_color = True

    def paintGL(self) -> None:
        if self.needs_update_clear_color:
            self.qfuncs.glClearColor(*self.built.cfg.background_color.rgb, 1.)
            self.needs_update_clear_color = False
        self.qfuncs.glClear(0x00004000 | 0x00000100)    # GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT
        self.null_texture.use(FRAME_BUFFER_BINDING)
        ret = self.built.render_all(self.ctx, self.global_t, camera=self.inject_camera)
        self.rendered.emit()
        if not ret:
            self.error_occurred.emit()
