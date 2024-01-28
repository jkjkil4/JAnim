from PySide6.QtWidgets import QWidget

from janim.anims.timeline import TimelineAnim
from janim.gui.application import Application
from janim.utils.config import Config

from janim.gui.ui_AnimViewer import Ui_AnimViewer


class AnimViewer(QWidget):
    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.anim = anim

        self.ui = Ui_AnimViewer()
        self.ui.setupUi(self)

        self.ui.progressSilder.setRange(0, anim.global_range.end * Config.get.fps)
        self.ui.progressSilder.valueChanged.connect(lambda v: self.ui.glw.set_progress(v / Config.get.fps))

        self.ui.progressSilder.valueChanged.emit(0)

    @classmethod
    def views(cls, anim: TimelineAnim) -> None:
        app = Application()

        w = cls(anim)
        w.show()

        app.exec()
