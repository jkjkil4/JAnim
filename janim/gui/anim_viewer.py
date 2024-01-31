from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QHBoxLayout, QPushButton, QSlider, QVBoxLayout,
                               QWidget)

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
        self.play_timer.timeout.connect(lambda: self.progress_slider.setValue(self.progress_slider.value() + 1))
        self.switch_play_state()

    def setup_ui(self) -> None:
        self.glw = GLWidget(self.anim)
        self.fixed_ratio_widget = FixedRatioWidget(self.glw,
                                                   self.anim.timeline.camera.points.info.frame_size)

        self.btn = QPushButton('暂停/继续')
        self.btn.clicked.connect(self.switch_play_state)

        self.progress_slider = QSlider()
        self.progress_slider.setOrientation(Qt.Orientation.Horizontal)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.btn)
        bottom_layout.addWidget(self.progress_slider)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.fixed_ratio_widget)
        vlayout.addLayout(bottom_layout)

        self.setLayout(vlayout)
        self.setMinimumSize(200, 160)
        self.resize(800, 608)

    def set_play_state(self, playing: bool) -> None:
        if playing != self.play_timer.isActive():
            self.switch_play_state()

    def switch_play_state(self) -> None:
        if self.play_timer.isActive():
            self.play_timer.stop()
        else:
            self.play_timer.start(1000 // Config.get.fps)

    @classmethod
    def views(cls, anim: TimelineAnim) -> None:
        app = Application()

        w = cls(anim)
        w.show()

        app.exec()
