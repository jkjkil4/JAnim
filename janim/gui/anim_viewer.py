import os
import time
from bisect import bisect
from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QHideEvent, QIcon, QKeyEvent, QMouseEvent,
                           QPainter, QPaintEvent, QPen, QWheelEvent)
from PySide6.QtWidgets import (QFileDialog, QLabel, QMainWindow, QMessageBox,
                               QPushButton, QSizePolicy, QSplitter, QWidget)

from janim.anims.animation import Animation, TimeRange
from janim.anims.timeline import TimelineAnim
from janim.gui.application import Application
from janim.gui.fixed_ratio_widget import FixedRatioWidget
from janim.gui.glwidget import GLWidget
from janim.render.file_writer import FileWriter
from janim.utils.config import Config
from janim.utils.file_ops import get_janim_dir
from janim.utils.simple_functions import clip

TIMELINE_VIEW_MIN_DURATION = 0.5

# TODO: comment
# TODO: 鼠标悬停在时间轴的动画上时，显示动画预览


class AnimViewer(QMainWindow):
    def __init__(self, anim: TimelineAnim, auto_play=True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.anim = anim

        self.setup_ui()

        self.timeline_view.value_changed.connect(self.on_value_changed)
        self.timeline_view.dragged.connect(lambda: self.set_play_state(False))
        self.timeline_view.space_pressed.connect(lambda: self.switch_play_state())
        self.timeline_view.value_changed.emit(0)

        self.btn_export.clicked.connect(self.on_export_clicked)

        self.play_timer = QTimer(self)
        self.play_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.play_timer.timeout.connect(self.on_play_timer_timeout)
        if auto_play:
            self.switch_play_state()

        self.fps_counter = 0
        self.fps_record_start = time.time()

        self.glw.rendered.connect(self.on_glw_rendered)

    def setup_ui(self) -> None:
        self.setup_status_bar()
        self.setup_central_widget()

    def setup_status_bar(self) -> None:
        self.fps_label = QLabel()
        self.time_label = QLabel()
        self.btn_export = QPushButton()
        self.btn_export.setIcon(QIcon(os.path.join(get_janim_dir(), 'gui', 'export.png')))
        self.btn_export.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        stb = self.statusBar()
        stb.setContentsMargins(0, 0, 0, 0)
        stb.addWidget(self.fps_label)
        stb.addPermanentWidget(self.time_label)
        stb.addPermanentWidget(self.btn_export)

    def setup_central_widget(self) -> None:
        self.glw = GLWidget(self.anim)
        self.fixed_ratio_widget = FixedRatioWidget(
            self.glw,
            (Config.get.pixel_width, Config.get.pixel_height)
        )

        self.btn = QPushButton('暂停/继续')
        self.btn.clicked.connect(self.switch_play_state)

        self.timeline_view = TimelineView(self.anim)
        self.timeline_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.vsplitter = QSplitter()
        self.vsplitter.setOrientation(Qt.Orientation.Vertical)
        self.vsplitter.addWidget(self.fixed_ratio_widget)
        self.vsplitter.addWidget(self.timeline_view)
        self.vsplitter.setSizes([400, 100])
        self.vsplitter.setStyleSheet('''QSplitter { background: rgb(25, 35, 45); }''')

        self.setCentralWidget(self.vsplitter)
        self.setMinimumSize(200, 160)
        self.resize(800, 608)
        self.setWindowTitle('JAnim Graphics')

    def hideEvent(self, event: QHideEvent) -> None:
        super().hideEvent(event)
        self.play_timer.stop()

    def on_value_changed(self, value: int) -> None:
        time = value / Config.get.preview_fps
        self.glw.set_time(time)
        self.time_label.setText(f'{time:.1f}/{self.anim.global_range.duration:.1f} s')

    def on_play_timer_timeout(self) -> None:
        self.timeline_view.set_progress(self.timeline_view.progress() + 1)
        if self.timeline_view.at_end():
            self.play_timer.stop()

    def on_glw_rendered(self) -> None:
        cur = time.time()
        self.fps_counter += 1
        if cur - self.fps_record_start >= 1:
            self.fps_label.setText(f'Preview FPS: {self.fps_counter}/{Config.get.preview_fps}')
            self.fps_counter = 0
            self.fps_record_start = cur

    def on_export_clicked(self) -> None:
        self.play_timer.stop()

        file_path = QFileDialog.getSaveFileName(
            self,
            '',
            os.path.join(Config.get.output_dir, f'{self.anim.timeline.__class__.__name__}.mp4'),
            'MP4 (*.mp4);;MOV (*.mov)'
        )
        file_path = file_path[0]
        if not file_path:
            return

        QMessageBox.information(self, '提示', '即将进行输出，请留意控制台信息')
        FileWriter.writes(self.anim.timeline.__class__().build(), file_path)
        QMessageBox.information(self, '提示', f'已完成输出至 {file_path}')

    def set_play_state(self, playing: bool) -> None:
        if playing != self.play_timer.isActive():
            self.switch_play_state()

    def switch_play_state(self) -> None:
        if self.play_timer.isActive():
            self.play_timer.stop()
        else:
            if self.timeline_view.at_end():
                self.timeline_view.set_progress(0)
            self.fps_record_start = time.time()
            self.fps_counter = 0
            self.play_timer.start(1000 // Config.get.preview_fps)

    @classmethod
    def views(cls, anim: TimelineAnim) -> None:
        app = Application.instance()
        if app is None:
            app = Application()

        w = cls(anim)
        w.show()

        app.exec()


class TimelineView(QWidget):
    @dataclass
    class LabelInfo:
        anim: Animation
        row: int

    @dataclass
    class PixelRange:
        left: float
        width: float

        @property
        def right(self) -> float:
            return self.left + self.width

    @dataclass
    class Pressing:
        w: bool = False
        a: bool = False
        s: bool = False
        d: bool = False

    value_changed = Signal(float)
    dragged = Signal()

    space_pressed = Signal()

    label_height = 32   # px
    play_space = 20     # px

    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None):
        super().__init__(parent)
        self.range = TimeRange(0, min(20, anim.global_range.duration))
        self.y_offset = 0
        self.anim = anim
        self._progress = 0
        self._maximum = round(anim.global_range.end * Config.get.preview_fps)

        self.is_pressing = TimelineView.Pressing()

        self.key_timer = QTimer(self)
        self.key_timer.timeout.connect(self.on_key_timer_timeout)
        self.key_timer.start(1000 // 60)

        self.init_label_info()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def init_label_info(self) -> None:
        self.labels_info: list[TimelineView.LabelInfo] = []
        self.max_row = 0

        self.flatten = self.anim.user_anim.flatten()[1:]
        self._sorted_anims = None

        stack: list[Animation] = []
        for anim in self.flatten:
            while stack and stack[-1].global_range.end <= anim.global_range.at:
                stack.pop()

            self.labels_info.append(TimelineView.LabelInfo(anim, len(stack)))
            self.max_row = max(self.max_row, len(stack))
            stack.append(anim)

    def get_sorted_anims(self) -> list[Animation]:
        if self._sorted_anims is None:
            self._sorted_anims = sorted(self.flatten, key=lambda x: x.global_range.at)
        return self._sorted_anims

    def move_range_to(self, at: float) -> None:
        self.range.at = clip(at, 0, self.anim.global_range.duration - self.range.duration)

    def on_key_timer_timeout(self) -> None:
        if self.is_pressing.w:
            cursor_time = self.pixel_to_time(self.mapFromGlobal(self.cursor().pos()).x())

            factor = max(TIMELINE_VIEW_MIN_DURATION / self.range.duration, 0.97)
            self.range.duration *= factor
            self.move_range_to(factor * (self.range.at - cursor_time) + cursor_time)

            self.update()

        elif self.is_pressing.s:
            cursor_time = self.pixel_to_time(self.mapFromGlobal(self.cursor().pos()).x())

            factor = min(self.anim.global_range.duration / self.range.duration, 1 / 0.97)
            self.range.duration *= factor
            self.move_range_to(factor * (self.range.at - cursor_time) + cursor_time)

            self.update()

        if self.is_pressing.a or self.is_pressing.d:
            shift = self.range.duration * 0.05 * (self.is_pressing.d - self.is_pressing.a)
            self.move_range_to(self.range.at + shift)

            self.update()

    def set_progress(self, progress: float) -> None:
        progress = clip(progress, 0, self._maximum)
        if progress != self._progress:
            self._progress = progress

            pixel_at = self.progress_to_pixel(progress)
            minimum = self.play_space
            maximum = self.width() - self.play_space
            if pixel_at < minimum:
                self.move_range_to(self.pixel_to_time(pixel_at - minimum))
            if pixel_at > maximum:
                self.move_range_to(self.pixel_to_time(pixel_at - maximum))

            self.value_changed.emit(progress)
            self.update()

    def progress(self) -> int:
        return self._progress

    def at_end(self) -> bool:
        return self._progress == self._maximum

    def progress_to_time(self, progress: int) -> float:
        return progress / Config.get.preview_fps

    def time_to_progress(self, time: float) -> int:
        return round(time * Config.get.preview_fps)

    def time_to_pixel(self, time: float) -> float:
        return (time - self.range.at) / self.range.duration * self.width()

    def pixel_to_time(self, pixel: float) -> float:
        return pixel / self.width() * self.range.duration + self.range.at

    def progress_to_pixel(self, progress: int) -> float:
        return self.time_to_pixel(self.progress_to_time(progress))

    def pixel_to_progress(self, pixel: float) -> int:
        return self.time_to_progress(self.pixel_to_time(pixel))

    def time_range_to_pixel_range(self, range: TimeRange) -> PixelRange:
        left = (range.at - self.range.at) / self.range.duration * self.width()
        width = range.duration / self.range.duration * self.width()
        return TimelineView.PixelRange(left, width)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_progress(self.pixel_to_progress(event.position().x()))
            self.dragged.emit()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.set_progress(self.pixel_to_progress(event.position().x()))
            self.dragged.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()

        if key == Qt.Key.Key_Space:
            self.space_pressed.emit()

        elif key == Qt.Key.Key_W:
            self.is_pressing.w = True
        elif key == Qt.Key.Key_A:
            self.is_pressing.a = True
        elif key == Qt.Key.Key_S:
            self.is_pressing.s = True
        elif key == Qt.Key.Key_D:
            self.is_pressing.d = True

        elif key == Qt.Key.Key_Z:
            anims = self.get_sorted_anims()
            time = self.progress_to_time(self._progress)
            idx = bisect(anims, time - 1e-5, key=lambda x: x.global_range.at)
            idx -= 1
            if idx < 0:
                self.set_progress(0)
            else:
                self.set_progress(self.time_to_progress(anims[idx].global_range.at))

            self.dragged.emit()

        elif key == Qt.Key.Key_C:
            anims = self.get_sorted_anims()
            time = self.progress_to_time(self._progress)
            idx = bisect(anims, time + 1e-5, key=lambda x: x.global_range.at)
            if idx < len(anims):
                self.set_progress(self.time_to_progress(anims[idx].global_range.at))
            else:
                self.set_progress(self.time_to_progress(self.anim.global_range.end))

            self.dragged.emit()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        key = event.key()

        if key == Qt.Key.Key_W:
            self.is_pressing.w = False
        elif key == Qt.Key.Key_A:
            self.is_pressing.a = False
        elif key == Qt.Key.Key_S:
            self.is_pressing.s = False
        elif key == Qt.Key.Key_D:
            self.is_pressing.d = False

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.y_offset = clip(self.y_offset - event.angleDelta().y() / 240 * self.label_height,
                             0,
                             self.max_row * self.label_height)
        self.update()

    def paintEvent(self, _: QPaintEvent) -> None:
        p = QPainter(self)

        for info in self.labels_info:
            if info.anim.global_range.end <= self.range.at or info.anim.global_range.at >= self.range.end:
                continue

            range = self.time_range_to_pixel_range(info.anim.global_range)
            rect = QRectF(range.left, -self.y_offset + info.row * self.label_height, range.width, self.label_height)
            if rect.x() < 0:
                rect.setX(0)

            if rect.width() > 5:
                x_adjust = 2
            elif rect.width() > 1:
                x_adjust = (rect.width() - 1) / 2
            else:
                x_adjust = 0
            rect.adjust(x_adjust, 2, -x_adjust, -2)

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(*info.anim.label_color).lighter())
            p.drawRect(rect)

            rect.adjust(1, 1, -1, -1)

            p.setPen(Qt.GlobalColor.black)
            p.drawText(
                rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                f'{info.anim.__class__.__name__}'
            )

        pixel_at = self.progress_to_pixel(self._progress)

        p.setPen(QPen(Qt.GlobalColor.white, 2))
        p.drawLine(pixel_at, 0, pixel_at, self.height())

        left = self.range.at / self.anim.global_range.duration * self.width()
        width = self.range.duration / self.anim.global_range.duration * self.width()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(77, 102, 132))
        p.drawRoundedRect(left, self.height() - 4, width, 4, 2, 2)
