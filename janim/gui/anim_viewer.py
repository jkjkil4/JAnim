import itertools as it
from dataclasses import dataclass

from PySide6.QtCore import QRect, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QKeyEvent, QMouseEvent, QPainter,
                           QPaintEvent, QPen)
from PySide6.QtWidgets import (QHBoxLayout, QPushButton, QSizePolicy,
                               QSplitter, QWidget)

from janim.anims.animation import Animation, TimeRange
from janim.anims.timeline import TimelineAnim
from janim.gui.application import Application
from janim.gui.fixed_ratio_widget import FixedRatioWidget
from janim.gui.glwidget import GLWidget
from janim.utils.config import Config
from janim.utils.simple_functions import clip

# TODO: comment


class AnimViewer(QWidget):
    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.anim = anim

        self.setup_ui()

        self.timeline_view.dragged.connect(lambda: self.set_play_state(False))
        self.timeline_view.value_changed.connect(lambda v: self.glw.set_progress(v / Config.get.preview_fps))

        self.timeline_view.value_changed.emit(0)

        self.play_timer = QTimer(self)
        self.play_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.play_timer.timeout.connect(self.on_play_timer_timeout)
        self.switch_play_state()

        self.setWindowTitle('JAnim Graphics')

    def setup_ui(self) -> None:
        self.glw = GLWidget(self.anim)
        self.fixed_ratio_widget = FixedRatioWidget(
            self.glw,
            (Config.get.pixel_width, Config.get.pixel_height)
        )

        self.btn = QPushButton('暂停/继续')
        self.btn.clicked.connect(self.switch_play_state)

        self.timeline_view = TimelineView(self.anim)
        self.timeline_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.timeline_view.space_pressed.connect(lambda: self.switch_play_state())

        self.vsplitter = QSplitter()
        self.vsplitter.setOrientation(Qt.Orientation.Vertical)
        self.vsplitter.addWidget(self.fixed_ratio_widget)
        self.vsplitter.addWidget(self.timeline_view)
        self.vsplitter.setSizes([400, 100])
        self.vsplitter.setStyleSheet('''QSplitter { background: rgb(25, 35, 45); }''')

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.vsplitter)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)
        self.setMinimumSize(200, 160)
        self.resize(800, 608)

    def on_play_timer_timeout(self) -> None:
        self.timeline_view.set_progress(self.timeline_view.progress() + 1)
        if self.timeline_view.at_end():
            self.play_timer.stop()

    def set_play_state(self, playing: bool) -> None:
        if playing != self.play_timer.isActive():
            self.switch_play_state()

    def switch_play_state(self) -> None:
        if self.play_timer.isActive():
            self.play_timer.stop()
        else:
            if self.timeline_view.at_end():
                self.timeline_view.set_progress(0)
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

    value_changed = Signal(float)
    dragged = Signal()

    space_pressed = Signal()

    label_height = 32

    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None):
        super().__init__(parent)
        self.range = TimeRange(0, anim.global_range.duration)
        self.anim = anim
        self._progress = 0
        self._maximum = round(anim.global_range.end * Config.get.preview_fps)

        self.init_label_info()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def init_label_info(self) -> None:
        self.labels_info: list[TimelineView.LabelInfo] = []

        flatten = self.anim.user_anim.flatten(sort_by_time=True)[1:]
        stack: list[Animation] = []
        for anim in flatten:
            while stack and stack[-1].global_range.end <= anim.global_range.at:
                stack.pop()

            self.labels_info.append(TimelineView.LabelInfo(anim, len(stack)))
            stack.append(anim)

    def set_progress(self, progress: float) -> None:
        progress = clip(progress, 0, self._maximum)
        if progress != self._progress:
            self._progress = progress
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
        if event.key() == Qt.Key.Key_Space:
            self.space_pressed.emit()

    def paintEvent(self, _: QPaintEvent) -> None:
        p = QPainter(self)

        colors = [Qt.GlobalColor.red, Qt.GlobalColor.green, Qt.GlobalColor.blue]

        p.setPen(Qt.PenStyle.NoPen)
        for info, color in zip(self.labels_info, it.cycle(colors)):
            range = self.time_range_to_pixel_range(info.anim.global_range)
            rect = QRect(range.left, info.row * self.label_height, range.width, self.label_height)
            rect.adjust(2, 2, -2, -2)

            p.setBrush(QColor(color).lighter())
            p.drawRect(rect)

        pixel_at = clip(self.progress_to_pixel(self._progress), 0, self.width())

        p.setPen(QPen(Qt.GlobalColor.white, 2))
        p.drawLine(pixel_at, 0, pixel_at, self.height())
