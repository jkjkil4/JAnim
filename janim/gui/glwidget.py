
import traceback

import moderngl as mgl
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import QEvent, QTimer, QSize

from janim.anims.animation import Animation
from janim.anims.timeline import TimelineAnim
from janim.render.base import Renderer, RenderData, program_map


MAX_RESIZE_RATE = 20
MIN_RESIZE_DURATION = 1000 // MAX_RESIZE_RATE


class GLWidget(QOpenGLWidget):
    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.anim = anim

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

        timeline = self.anim.timeline
        camera_data = timeline.get_stored_data_at_time(timeline.camera, self._progress)
        camera_info = camera_data.cmpt.points.info

        render_token = Renderer.data_ctx.set(RenderData(ctx=self.ctx, camera_info=camera_info))
        global_t_token = Animation.global_t_ctx.set(self._progress)

        view_matrix_f4 = camera_info.view_matrix.T.astype('f4').flatten()
        proj_matrix_f4 = camera_info.proj_matrix.T.astype('f4').flatten()
        frame_radius_f4 = camera_info.frame_radius.astype('f4')

        for prog in program_map.values():
            if 'JA_VIEW_MATRIX' in prog._members:
                prog['JA_VIEW_MATRIX'] = view_matrix_f4
            if 'JA_PROJ_MATRIX' in prog._members:
                prog['JA_PROJ_MATRIX'] = proj_matrix_f4
            if 'JA_FRAME_RADIUS' in prog._members:
                prog['JA_FRAME_RADIUS'] = frame_radius_f4

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
