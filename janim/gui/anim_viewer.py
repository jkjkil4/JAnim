from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPaintEvent, QPainter, QColor
from PySide6.QtWidgets import (QHBoxLayout, QPushButton, QSizePolicy, QSlider,
                               QSplitter, QVBoxLayout, QWidget)

from janim.anims.animation import Animation, TimeRange
from janim.anims.composition import AnimGroup
from janim.anims.timeline import TimelineAnim
from janim.gui.application import Application
from janim.gui.fixed_ratio_widget import FixedRatioWidget
from janim.gui.glwidget import GLWidget
from janim.utils.config import Config

# TODO: comment


class AnimViewer(QWidget):
    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.anim = anim

        self.setup_ui()

        self.progress_slider.setRange(0, anim.global_range.end * Config.get.fps)
        self.progress_slider.sliderMoved.connect(lambda: self.set_play_state(False))
        self.progress_slider.valueChanged.connect(lambda v: self.glw.set_progress(v / Config.get.fps))

        self.progress_slider.valueChanged.emit(0)

        self.play_timer = QTimer(self)
        self.play_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.play_timer.timeout.connect(self.on_play_timer_timeout)
        self.switch_play_state()

    def setup_ui(self) -> None:
        self.glw = GLWidget(self.anim)
        self.fixed_ratio_widget = FixedRatioWidget(self.glw,
                                                   self.anim.timeline.camera.points.info.frame_size)

        self.btn = QPushButton('暂停/继续')
        self.btn.clicked.connect(self.switch_play_state)

        # self.timeline_view = TimelineView(self.anim)
        # self.timeline_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # self.vsplitter = QSplitter()
        # self.vsplitter.setOrientation(Qt.Orientation.Vertical)
        # self.vsplitter.addWidget(self.fixed_ratio_widget)
        # self.vsplitter.addWidget(self.timeline_view)
        # self.vsplitter.setSizes([400, 100])
        # self.vsplitter.setStyleSheet('''QSplitter { background: rgb(25, 35, 45); }''')

        self.progress_slider = QSlider()
        self.progress_slider.setOrientation(Qt.Orientation.Horizontal)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.btn)
        bottom_layout.addWidget(self.progress_slider)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.fixed_ratio_widget)
        vlayout.addLayout(bottom_layout)

        # main_layout = QHBoxLayout()
        # main_layout.addWidget(self.vsplitter)
        # main_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(vlayout)
        self.setMinimumSize(200, 160)
        self.resize(800, 608)

    def on_play_timer_timeout(self) -> None:
        self.progress_slider.setValue(self.progress_slider.value() + 1)
        if self.progress_slider.value() == self.progress_slider.maximum():
            self.play_timer.stop()

    def set_play_state(self, playing: bool) -> None:
        if playing != self.play_timer.isActive():
            self.switch_play_state()

    def switch_play_state(self) -> None:
        if self.play_timer.isActive():
            self.play_timer.stop()
        else:
            if self.progress_slider.value() == self.progress_slider.maximum():
                self.progress_slider.setValue(0)
            self.play_timer.start(1000 // Config.get.fps)

    @classmethod
    def views(cls, anim: TimelineAnim) -> None:
        app = Application()

        w = cls(anim)
        w.show()

        app.exec()


class TimelineView(QWidget):
    @dataclass
    class LabelInfo:
        anim: Animation
        row: int

    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None):
        super().__init__(parent)
        self.range = TimeRange(0, anim.global_range.duration)
        self.anim = anim

        self.init_label_info()

    def init_label_info(self) -> None:
        self.labels_info: list[TimelineView.LabelInfo] = []

        flatten = self.anim.user_anim.flatten(sort_by_time=True)[1:]
        stack: list[Animation] = []
        for anim in flatten:
            while stack and stack[-1].global_range.end <= anim.global_range.at:
                stack.pop()

            self.labels_info.append(TimelineView.LabelInfo(anim, len(stack)))
            stack.append(anim)

        for info in self.labels_info:
            print(info.row, info.anim.__class__.__name__, info.anim.global_range)

    def paintEvent(self, event: QPaintEvent) -> None:
        # p = QPainter(self)
        pass
