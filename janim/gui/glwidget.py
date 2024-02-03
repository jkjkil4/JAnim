
import heapq
import traceback

import moderngl as mgl
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from janim.anims.animation import Animation
from janim.anims.timeline import TimelineAnim
from janim.render.base import RenderData, Renderer, program_map
from janim.utils.config import Config

MAX_RESIZE_RATE = 20
MIN_RESIZE_DURATION = 1000 // MAX_RESIZE_RATE


class GLWidget(QOpenGLWidget):
    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.anim = anim
        self.flattened = anim.flatten()

        self._progress: float | None = None

    def set_progress(self, progress: float) -> None:
        self._progress = progress

        token = Animation.global_t_ctx.set(progress)
        self.anim.anim_on(progress)
        Animation.global_t_ctx.reset(token)

        self.update()

    def initializeGL(self) -> None:
        self.ctx = mgl.create_context()
        self.ctx.enable(mgl.BLEND)

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
            if 'JA_ANTI_ALIAS_RADIUS' in prog._members:
                prog['JA_ANTI_ALIAS_RADIUS'] = Config.get.anti_alias_width / 2

        try:
            render_calls = heapq.merge(
                *[
                    anim.render_call_list
                    for anim in self.flattened
                    if anim.render_call_list and anim.global_range.at <= self._progress < anim.global_range.end
                ],
                key=lambda x: x.depth,
                reverse=True
            )
            for render_call in render_calls:
                render_call.func()

        except Exception:
            traceback.print_exc()

        Animation.global_t_ctx.reset(global_t_token)
        Renderer.data_ctx.reset(render_token)
