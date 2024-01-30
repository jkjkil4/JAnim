from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider, QWidget, QVBoxLayout

from janim.anims.timeline import TimelineAnim
from janim.gui.application import Application
from janim.gui.fixed_ratio_widget import FixedRatioWidget
from janim.gui.glwidget import GLWidget
from janim.utils.config import Config


class AnimViewer(QWidget):
    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.anim = anim

        self.setup_ui()

        self.progress_slider.setRange(0, anim.global_range.end * Config.get.fps)
        self.progress_slider.valueChanged.connect(lambda v: self.glw.set_progress(v / Config.get.fps))

        self.progress_slider.valueChanged.emit(0)

    def setup_ui(self) -> None:
        self.glw = GLWidget(self.anim)
        self.fixed_ratio_widget = FixedRatioWidget(self.glw,
                                                   self.anim.timeline.camera.points.info.frame_size)

        self.progress_slider = QSlider()
        self.progress_slider.setOrientation(Qt.Orientation.Horizontal)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.fixed_ratio_widget)
        vlayout.addWidget(self.progress_slider)

        self.setLayout(vlayout)
        self.setMinimumSize(200, 160)
        self.resize(800, 608)

    @classmethod
    def views(cls, anim: TimelineAnim) -> None:
        app = Application()

        w = cls(anim)
        w.show()

        app.exec()
